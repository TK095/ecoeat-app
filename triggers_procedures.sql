-- ============================================================
-- Group ID  : [Insert Your Group ID, e.g., Group 05]
-- Date      : 2025-05-22
-- Purpose   : EcoEat – Triggers and Stored Procedure (MySQL 8.0+)
-- ============================================================

USE ecoeat;

DELIMITER $$

-- ────────────────────────────────────────────────────────────
-- TRIGGER 1 : trg_decrease_stock
--   Fires    : BEFORE INSERT on `Order`
--   Purpose  : Decrease stockQuantity by 1 when a new order
--              is placed. Rejects the order if stock is 0.
--              Optionally rejects if current time is past
--              the box's pickUpDeadline.
-- ────────────────────────────────────────────────────────────
CREATE TRIGGER trg_decrease_stock
BEFORE INSERT ON `Order`
FOR EACH ROW
BEGIN
    DECLARE v_stock         INT;
    DECLARE v_deadline      TIME;
    DECLARE v_now_time      TIME;

    -- Fetch current stock and deadline for the requested box
    SELECT stockQuantity, pickUpDeadline
      INTO v_stock, v_deadline
      FROM Blind_Box
     WHERE box_ID = NEW.box_ID;

    -- (Optional) Reject if ordering after pick-up deadline
    SET v_now_time = CURTIME();
    IF v_now_time > v_deadline THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Order rejected: pick-up deadline has passed for this box.';
    END IF;

    -- Reject if out of stock
    IF v_stock <= 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Order rejected: this Blind Box is out of stock.';
    END IF;

    -- Decrease stock
    UPDATE Blind_Box
       SET stockQuantity = stockQuantity - 1
     WHERE box_ID = NEW.box_ID;
END$$


-- ────────────────────────────────────────────────────────────
-- TRIGGER 2 : trg_award_eco_points
--   Fires    : AFTER UPDATE on `Order`
--   Purpose  : When status changes TO 'Claimed', calculate
--              eco-points = FLOOR(originalPrice - flashPrice)
--              and add them to the student's eco_points.
-- ────────────────────────────────────────────────────────────
CREATE TRIGGER trg_award_eco_points
AFTER UPDATE ON `Order`
FOR EACH ROW
BEGIN
    DECLARE v_original  DECIMAL(8,2);
    DECLARE v_flash     DECIMAL(8,2);
    DECLARE v_points    INT;

    -- Only act when status transitions to 'Claimed'
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
--   Purpose  : Safely place a new order inside a transaction.
--              Generates a random 6-char alphanumeric pick-up
--              code, sets totalAmount = flashPrice, and calls
--              INSERT (which fires trg_decrease_stock).
--
--   Parameters:
--     IN  p_SID       INT    – student placing the order
--     IN  p_box_ID    INT    – blind box being ordered
--     OUT p_order_ID  INT    – newly created order ID
--     OUT p_pickCode  VARCHAR(10) – generated pick-up code
-- ────────────────────────────────────────────────────────────
CREATE PROCEDURE sp_place_order (
    IN  p_SID       INT,
    IN  p_box_ID    INT,
    OUT p_order_ID  INT,
    OUT p_pickCode  VARCHAR(10)
)
BEGIN
    DECLARE v_flash     DECIMAL(8,2);
    DECLARE v_code      VARCHAR(10);
    DECLARE v_exists    INT DEFAULT 1;

    -- Exit handler rolls back on any SQL error
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    -- Get flash price for the box
    SELECT flashPrice
      INTO v_flash
      FROM Blind_Box
     WHERE box_ID = p_box_ID;

    -- Generate a unique 6-character alphanumeric pick-up code
    WHILE v_exists > 0 DO
        SET v_code = UPPER(SUBSTRING(MD5(RAND()), 1, 6));
        SELECT COUNT(*) INTO v_exists
          FROM `Order`
         WHERE pickUpCode = v_code;
    END WHILE;

    -- Insert the order (trg_decrease_stock fires here)
    INSERT INTO `Order` (SID, box_ID, totalAmount, pickUpCode, status)
    VALUES (p_SID, p_box_ID, v_flash, v_code, 'Pending');

    SET p_order_ID = LAST_INSERT_ID();
    SET p_pickCode = v_code;

    COMMIT;
END$$


DELIMITER ;
