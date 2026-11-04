-- ==========================================================
-- H₂SENSE: H₂S Exposure Detection Database Schema
-- Compatible with MySQL 5.7+ / 8.0+ / MariaDB / WAMP Server
-- ==========================================================

CREATE DATABASE IF NOT EXISTS `h2sense` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `h2sense`;

-- Drop existing tables in reverse dependency order
DROP TABLE IF EXISTS `exposure_records`;
DROP TABLE IF EXISTS `badges`;
DROP TABLE IF EXISTS `workers`;
DROP TABLE IF EXISTS `calibration_points`;

-- ----------------------------------------------------------
-- 1. Workers Table
-- ----------------------------------------------------------
CREATE TABLE `workers` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `worker_code` VARCHAR(32) NOT NULL UNIQUE,
    `name` VARCHAR(128) NOT NULL,
    `department` VARCHAR(100) NOT NULL,
    `role` VARCHAR(100) NOT NULL,
    `phone` VARCHAR(32) NULL,
    `status` ENUM('ACTIVE', 'INACTIVE') DEFAULT 'ACTIVE',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------
-- 2. Badges Table
-- ----------------------------------------------------------
CREATE TABLE `badges` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `badge_code` VARCHAR(32) NOT NULL UNIQUE,
    `worker_id` INT NOT NULL,
    `activation_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `expiry_date` DATETIME NOT NULL,
    `status` ENUM('ACTIVE', 'EXPIRED', 'REVOKED') DEFAULT 'ACTIVE',
    CONSTRAINT `fk_badges_worker` FOREIGN KEY (`worker_id`) 
        REFERENCES `workers`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------
-- 3. Exposure Records Table
-- ----------------------------------------------------------
CREATE TABLE `exposure_records` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `worker_id` INT NOT NULL,
    `badge_id` INT NOT NULL,
    `timestamp` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `scan_type` ENUM('ENTRY', 'EXIT') NOT NULL,
    `r` INT NOT NULL,
    `g` INT NOT NULL,
    `b` INT NOT NULL,
    `lab_l` FLOAT NOT NULL,
    `lab_a` FLOAT NOT NULL,
    `lab_b` FLOAT NOT NULL,
    `temperature` FLOAT NOT NULL DEFAULT 25.0,
    `humidity` FLOAT NOT NULL DEFAULT 50.0,
    `raw_exposure` FLOAT NOT NULL,
    `corrected_exposure` FLOAT NOT NULL,
    `shift_exposure` FLOAT NOT NULL DEFAULT 0.0,
    `cumulative_exposure` FLOAT NOT NULL DEFAULT 0.0,
    `status` ENUM('SAFE', 'CAUTION', 'HIGH', 'CRITICAL') NOT NULL,
    `confidence` FLOAT NOT NULL DEFAULT 0.95,
    CONSTRAINT `fk_records_worker` FOREIGN KEY (`worker_id`) 
        REFERENCES `workers`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_records_badge` FOREIGN KEY (`badge_id`) 
        REFERENCES `badges`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------
-- 4. Calibration Points Table
-- ----------------------------------------------------------
CREATE TABLE `calibration_points` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `exposure_value` FLOAT NOT NULL,
    `r` INT NOT NULL,
    `g` INT NOT NULL,
    `b` INT NOT NULL,
    `lab_l` FLOAT NOT NULL,
    `lab_a` FLOAT NOT NULL,
    `lab_b` FLOAT NOT NULL,
    `temperature` FLOAT NOT NULL DEFAULT 25.0,
    `humidity` FLOAT NOT NULL DEFAULT 50.0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------
-- Initial Calibration Prototype Data
-- Baseline colorimetric curve: Green (Safe) -> Yellow -> Orange -> Deep Red/Brown (Critical)
-- ----------------------------------------------------------
INSERT INTO `calibration_points` (`exposure_value`, `r`, `g`, `b`, `lab_l`, `lab_a`, `lab_b`, `temperature`, `humidity`) VALUES
(0.0,   34, 197, 94,   70.5, -60.2,  41.5, 25.0, 50.0),   -- 0: Vibrant Safe Green
(10.0,  95, 207, 72,   74.2, -49.6,  53.1, 25.0, 50.0),   -- 10: Lime/Light Green
(25.0, 163, 230, 53,   83.1, -38.4,  68.2, 25.0, 50.0),   -- 25: Chartreuse/Yellow-Green
(50.0, 234, 179,  8,   75.3,   6.2,  76.4, 25.0, 50.0),   -- 50: Amber/Caution Yellow
(75.0, 249, 115, 22,   63.1,  48.2,  65.5, 25.0, 50.0),   -- 75: High Exposure Orange
(100.0, 239,  68, 68,  53.2,  67.1,  48.8, 25.0, 50.0),   -- 100: Warning Red
(150.0, 185,  28, 28,  37.4,  61.5,  43.2, 25.0, 50.0),   -- 150: Deep Red
(200.0, 127,  29, 29,  26.8,  44.9,  28.6, 25.0, 50.0);   -- 200: Critical Dark Red/Brown
