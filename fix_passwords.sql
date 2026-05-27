-- ============================================================
-- One-shot fix: replace the placeholder hash in the seed data
-- with a real Werkzeug scrypt hash for the password "password123".
--
-- After running this, every sample account can log in with:
--     password123
--
-- (The hash below was generated with werkzeug.security.generate_password_hash.
--  scrypt uses a random salt, so this exact string only verifies against
--  "password123" — do NOT reuse it for production users.)
-- ============================================================

USE ecoeat_2;

SET @real_hash = 'scrypt:32768:8:1$HsFIevUMAvogns6I$8ba26431c1f64edbf9ac52f04ef3c1b881956e10e8983ed959f86a18077afc6035db11db80debd942e4bc9f01ac311b319175e87e6802118f7af8e30716c28db';

UPDATE Student SET password_hash = @real_hash;
UPDATE Store   SET password_hash = @real_hash;

SELECT email, password_hash FROM Student;
SELECT email, password_hash FROM Store;
