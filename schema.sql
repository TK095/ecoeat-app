-- ============================================================
-- Group ID  : [Insert Your Group ID, e.g., Group 05]
-- Date      : 2025-05-22
-- Purpose   : EcoEat – Campus Surplus Food Rescue Platform
--             CREATE TABLE statements (MySQL 8.0+)
-- ============================================================

CREATE DATABASE IF NOT EXISTS ecoeat;
USE ecoeat;

-- ────────────────────────────────────────────────────────────
-- 1. Student
-- ────────────────────────────────────────────────────────────
CREATE TABLE Student (
    SID             INT             NOT NULL AUTO_INCREMENT,
    name            VARCHAR(100)    NOT NULL,
    student_number  VARCHAR(20)     NOT NULL,
    phone           VARCHAR(20)     NOT NULL,
    acc_balance     DECIMAL(10,2)   NOT NULL DEFAULT 0.00,
    eco_points      INT             NOT NULL DEFAULT 0,

    CONSTRAINT pk_student         PRIMARY KEY (SID),
    CONSTRAINT uq_student_number  UNIQUE      (student_number),
    CONSTRAINT chk_acc_balance    CHECK       (acc_balance  >= 0),
    CONSTRAINT chk_eco_points     CHECK       (eco_points   >= 0)
);

-- ────────────────────────────────────────────────────────────
-- 2. Store
-- ────────────────────────────────────────────────────────────
CREATE TABLE Store (
    store_ID    INT             NOT NULL AUTO_INCREMENT,
    name        VARCHAR(100)    NOT NULL,
    location    VARCHAR(200)    NOT NULL,
    category    VARCHAR(50)     NOT NULL,   -- e.g. Bakery, Chinese, Deli
    rating      DECIMAL(3,2)    NULL,

    CONSTRAINT pk_store        PRIMARY KEY (store_ID),
    CONSTRAINT chk_rating      CHECK (rating IS NULL OR (rating >= 0 AND rating <= 5))
);

-- ────────────────────────────────────────────────────────────
-- 3. Blind_Box
-- ────────────────────────────────────────────────────────────
CREATE TABLE Blind_Box (
    box_ID          INT             NOT NULL AUTO_INCREMENT,
    store_ID        INT             NOT NULL,
    name            VARCHAR(100)    NOT NULL,
    originalPrice   DECIMAL(8,2)    NOT NULL,
    flashPrice      DECIMAL(8,2)    NOT NULL,
    stockQuantity   INT             NOT NULL DEFAULT 0,
    pickUpDeadline  TIME            NOT NULL,   -- e.g. '20:00:00'

    CONSTRAINT pk_blind_box         PRIMARY KEY (box_ID),
    CONSTRAINT fk_box_store         FOREIGN KEY (store_ID)
                                        REFERENCES Store(store_ID)
                                        ON UPDATE CASCADE
                                        ON DELETE RESTRICT,
    CONSTRAINT chk_originalPrice    CHECK (originalPrice  > 0),
    CONSTRAINT chk_flashPrice       CHECK (flashPrice     > 0),
    CONSTRAINT chk_price_order      CHECK (flashPrice     < originalPrice),
    CONSTRAINT chk_stockQuantity    CHECK (stockQuantity  >= 0)
);

-- ────────────────────────────────────────────────────────────
-- 4. `Order`  (backtick-quoted because ORDER is reserved in MySQL)
-- ────────────────────────────────────────────────────────────
CREATE TABLE `Order` (
    order_ID    INT             NOT NULL AUTO_INCREMENT,
    SID         INT             NOT NULL,
    box_ID      INT             NOT NULL,
    orderTime   TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    totalAmount DECIMAL(8,2)    NOT NULL,
    pickUpCode  VARCHAR(10)     NOT NULL,
    status      VARCHAR(20)     NOT NULL DEFAULT 'Pending',

    CONSTRAINT pk_order         PRIMARY KEY (order_ID),
    CONSTRAINT uq_pickUpCode    UNIQUE      (pickUpCode),
    CONSTRAINT fk_order_student FOREIGN KEY (SID)
                                    REFERENCES Student(SID)
                                    ON UPDATE CASCADE
                                    ON DELETE RESTRICT,
    CONSTRAINT fk_order_box     FOREIGN KEY (box_ID)
                                    REFERENCES Blind_Box(box_ID)
                                    ON UPDATE CASCADE
                                    ON DELETE RESTRICT,
    CONSTRAINT chk_status       CHECK (status IN ('Pending','Claimed','Canceled')),
    CONSTRAINT chk_totalAmount  CHECK (totalAmount >= 0)
);

-- ────────────────────────────────────────────────────────────
-- 5. Review  (1:1 with Order via UNIQUE FK on order_ID)
-- ────────────────────────────────────────────────────────────
CREATE TABLE Review (
    review_ID   INT         NOT NULL AUTO_INCREMENT,
    order_ID    INT         NOT NULL,
    rating      INT         NOT NULL,
    comment     TEXT        NULL,
    photoURL    VARCHAR(500) NULL,

    CONSTRAINT pk_review        PRIMARY KEY (review_ID),
    CONSTRAINT uq_review_order  UNIQUE      (order_ID),       -- enforces 1:1
    CONSTRAINT fk_review_order  FOREIGN KEY (order_ID)
                                    REFERENCES `Order`(order_ID)
                                    ON UPDATE CASCADE
                                    ON DELETE CASCADE,
    CONSTRAINT chk_rev_rating   CHECK (rating BETWEEN 1 AND 5)
);
