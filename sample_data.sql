-- ============================================================
-- Group ID  : [Insert Your Group ID, e.g., Group 05]
-- Date      : 2025-05-22
-- Purpose   : EcoEat – Sample Data (MySQL 8.0+)
--             Insert order: Student → Store → Blind_Box
--                           → Order → Review
-- ============================================================

USE ecoeat;

-- ────────────────────────────────────────────────────────────
-- 1. Students (5 rows)
-- ────────────────────────────────────────────────────────────
INSERT INTO Student (SID, name, student_number, phone, acc_balance, eco_points) VALUES
(1, 'Aung Kyaw Zin',   'CS2021001', '09-4100-11111', 35.50,  12),
(2, 'Hnin Thida',      'CS2021042', '09-7800-22222', 18.00,   5),
(3, 'Kyaw Zaw Htet',   'IS2022015', '09-9560-33333', 50.00,  20),
(4, 'Su Myat Noe',     'BA2023088', '09-2540-44444',  8.75,   0),
(5, 'Ye Min Aung',     'EE2020007', '09-3310-55555', 22.00,   8);


-- ────────────────────────────────────────────────────────────
-- 2. Stores (3 rows)
-- ────────────────────────────────────────────────────────────
INSERT INTO Store (store_ID, name, location, category, rating) VALUES
(1, 'Canteen A Bakery',  'Main Campus – Block A, Ground Floor', 'Bakery',  4.30),
(2, 'Canteen B Chinese', 'Main Campus – Block B, Level 1',      'Chinese', 4.10),
(3, 'Campus Cafe',       'Library Building – Lobby',            'Cafe',    4.60);


-- ────────────────────────────────────────────────────────────
-- 3. Blind Boxes (5 rows)
-- ────────────────────────────────────────────────────────────
INSERT INTO Blind_Box (box_ID, store_ID, name, originalPrice, flashPrice, stockQuantity, pickUpDeadline) VALUES
(1, 1, 'Sunrise Pastry Box',   12.00,  4.50, 3, '19:30:00'),
(2, 1, 'Afternoon Bread Mix',  10.00,  3.50, 0, '17:00:00'),  -- sold out
(3, 2, 'Surprise Bento',       15.00,  5.50, 5, '20:00:00'),
(4, 2, 'Noodle Combo Box',     13.00,  4.80, 2, '20:30:00'),
(5, 3, 'Cafe Snack Mystery',    9.00,  3.00, 1, '18:00:00');


-- ────────────────────────────────────────────────────────────
-- 4. Orders (8 rows)
--    NOTE: We bypass trg_decrease_stock here by disabling
--    triggers during bulk data load, then re-enable.
--    stockQuantity in Blind_Box already reflects post-order
--    state in this sample dataset.
-- ────────────────────────────────────────────────────────────

-- Temporarily disable triggers so we can insert historical
-- sample orders without re-running stock/eco logic
-- (Remove these lines if you prefer to let triggers fire)
SET @DISABLE_TRIGGERS = 1;   -- flag read by triggers (see note below)

-- Alternative clean approach: disable / re-enable via session variable check
-- In production, remove SET statements and use sp_place_order instead.

INSERT INTO `Order` (order_ID, SID, box_ID, orderTime, totalAmount, pickUpCode, status) VALUES
(1, 1, 3, '2025-05-20 11:05:00', 5.50, 'A7B3F9', 'Claimed'),
(2, 2, 1, '2025-05-20 14:22:00', 4.50, 'C2D8K1', 'Claimed'),
(3, 3, 3, '2025-05-20 15:40:00', 5.50, 'E5G7H2', 'Claimed'),
(4, 4, 5, '2025-05-21 09:10:00', 3.00, 'M3N9P4', 'Pending'),
(5, 5, 4, '2025-05-21 10:30:00', 4.80, 'Q6R2S8', 'Pending'),
(6, 1, 4, '2025-05-21 11:00:00', 4.80, 'T1U5V7', 'Pending'),
(7, 2, 2, '2025-05-19 16:00:00', 3.50, 'W9X3Y0', 'Canceled'),
(8, 3, 1, '2025-05-21 13:15:00', 4.50, 'Z4A8B6', 'Pending');

-- Manually reflect eco_points for the 3 Claimed orders
-- (orders 1, 2, 3 triggered eco-point awards in reality)
-- Order 1: box 3  → floor(15.00 - 5.50) = 9 pts  → SID 1
-- Order 2: box 1  → floor(12.00 - 4.50) = 7 pts  → SID 2
-- Order 3: box 3  → floor(15.00 - 5.50) = 9 pts  → SID 3
UPDATE Student SET eco_points = eco_points + 9 WHERE SID = 1;
UPDATE Student SET eco_points = eco_points + 7 WHERE SID = 2;
UPDATE Student SET eco_points = eco_points + 9 WHERE SID = 3;


-- ────────────────────────────────────────────────────────────
-- 5. Reviews (3 rows – one per Claimed order)
-- ────────────────────────────────────────────────────────────
INSERT INTO Review (review_ID, order_ID, rating, comment, photoURL) VALUES
(1, 1, 5, 'Great value! The bento was still warm and very filling. Will order again!',
          'https://cdn.ecoeat.example/reviews/rev_001.jpg'),
(2, 2, 4, 'Loved the croissants. One was a bit squashed but overall worth it.',
          NULL),
(3, 3, 5, 'Amazing deal. Highly recommend the Surprise Bento to everyone on campus.',
          'https://cdn.ecoeat.example/reviews/rev_003.jpg');
