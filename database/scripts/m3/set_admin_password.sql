UPDATE app_user
SET password_hash = 'pbkdf2_sha256$210000$c2VudHJpeC1hZG1pbi1zYWx0LTIwMjY=$hm2DNTRC0ttsgaFsbXjkpgvtgH//kcQjaiEfu7EYmOA='
WHERE id = 'user-admin';
