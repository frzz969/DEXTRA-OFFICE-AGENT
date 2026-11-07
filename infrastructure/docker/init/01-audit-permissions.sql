-- Audit append-only di level database.
--
-- Hash chaining di aplikasi mendeteksi penyuntingan; izin database mencegahnya.
-- Keduanya dibutuhkan: rantai hash tidak berguna kalau penyerang bisa menulis
-- ulang seluruh rantai, dan izin saja tidak mendeteksi penyuntingan oleh
-- superuser.
GRANT SELECT, INSERT ON audit_events TO dextra;
REVOKE UPDATE, DELETE ON audit_events FROM dextra;

-- Urutan (seq) diberikan oleh aplikasi, bukan sequence, supaya hash mencakup
-- nomor urut. Karena itu INSERT harus boleh, tetapi UPDATE/DELETE tidak.
COMMENT ON TABLE audit_events IS 'Append-only: UPDATE dan DELETE dicabut dari role aplikasi.';
