-- ============================================================
-- EcoEat – Updated Triggers & Stored Procedure for the NEW schema
-- Run this AFTER new_schema.sql + new_sample_data.sql.
-- Idempotent: drops old definitions first.
-- ============================================================

USE ecoeat_2;

DROP TRIGGER   IF EXISTS trg_decrease_stock;
DROP TRIGGER   IF EXISTS trg_award_eco_points;
DROP PROCEDURE IF EXISTS sp_place_order;

DELIMITER $$

-- ────────────────────────────────────────────────────────────
-- TRIGGER 1 : trg_decrease_stock
--   BEFORE INSERT on `Order` — decrement stock, reject if 0
--   or past the pickup deadline.
-- ────────────────────────────────────────────────────────────
CREATE TRIGGER trg_decrease_stock
BEFORE INSERT ON `Order`
FOR EACH ROW
BEGIN
    DECLARE v_stock     INT;
    DECLARE v_deadline  TIME;
    DECLARE v_now_time  TIME;

    SELECT stockQuantity, pickUpDeadline
      INTO v_stock, v_deadline
      FROM Blind_Box
     WHERE box_ID = NEW.box_ID;

    SET v_now_time = CURTIME();
    IF v_now_time > v_deadline THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Order rejected: pick-up deadline has passed for this box.';
    END IF;

    IF v_stock <= 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Order rejected: this Blind Box is out of stock.';
    END IF;

    UPDATE Blind_Box
       SET stockQuantity = stockQuantity - 1
     WHERE box_ID = NEW.box_ID;
END$$


-- ────────────────────────────────────────────────────────────
-- TRIGGER 2 : trg_award_eco_points
--   AFTER UPDATE on `Order` — when status transitions to
--   'Claimed', award FLOOR(originalPrice - flashPrice) points.
-- ────────────────────────────────────────────────────────────
CREATE TRIGGER trg_award_eco_points
AFTER UPDATE ON `Order`
FOR EACH ROW
BEGIN
    DECLARE v_original  DECIMAL(8,2);
    DECLARE v_flash     DECIMAL(8,2);
    DECLARE v_points    INT;

    IF OLD.status <> 'Claimed' AND NEW.status = 'Claimed' THEN
        SELECT originalPrice, flashPrice
          INTO v_original, v_flash
          FROM Blind_Box
         WHERE box_ID = NEW.box_ID;

        SET v_points = FLOOR(v_original - v_flash);

        UPDATE Student
           SET eco_points = eco_points + v_points
         WHERE SID = NEW.SID;
    END IF;
END$$


-- ────────────────────────────────────────────────────────────
-- STORED PROCEDURE : sp_place_order
--   Generates a unique 6-char pickup code and inserts the
--   order. NOTE: new schema uses snake_case `pickup_code` and
--   no longer has `totalAmount`.
-- ────────────────────────────────────────────────────────────
CREATE PROCEDURE sp_place_order (
    IN  p_SID       INT,
    IN  p_box_ID    INT,
    OUT p_order_ID  INT,
    OUT p_pickCode  VARCHAR(10)
)
BEGIN
    DECLARE v_code   VARCHAR(10);
    DECLARE v_exists INT DEFAULT 1;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    WHILE v_exists > 0 DO
        SET v_code = UPPER(SUBSTRING(MD5(RAND()), 1, 6));
        SELECT COUNT(*) INTO v_exists
          FROM `Order`
         WHERE pickup_code = v_code;
    END WHILE;

    INSERT INTO `Order` (SID, box_ID, pickup_code, status)
    VALUES (p_SID, p_box_ID, v_code, 'Pending');

    SET p_order_ID = LAST_INSERT_ID();
    SET p_pickCode = v_code;

    COMMIT;
END$$

DELIMITER ;

-- Step 1: Turn on the MySQL Event Scheduler engine
SET GLOBAL event_scheduler = ON;

-- Step 2: Create the Event
DELIMITER $$

CREATE EVENT IF NOT EXISTS evt_auto_cleanup
ON SCHEDULE EVERY 5 MINUTE
-- NOTE: To create this without it running immediately during your demo, 
-- you can uncomment the line below:
-- DISABLE
DO
BEGIN
    -- ACTION 1: Penalize no-shows. Cancel any pending orders where the deadline passed.
    UPDATE `Order` o
    JOIN Blind_Box b ON o.box_ID = b.box_ID
    SET o.status = 'Canceled'
    WHERE o.status = 'Pending' AND NOW() > b.pickUpDeadline;

    -- ACTION 2: Auto-hide the expired boxes from the marketplace.
    UPDATE Blind_Box
    SET is_active = FALSE
    WHERE is_active = TRUE AND NOW() > pickUpDeadline;
    
END$$

DELIMITER ;
