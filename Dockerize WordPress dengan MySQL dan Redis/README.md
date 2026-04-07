# 🐳 WordPress + MySQL + Redis (Docker Compose)

## 📌 Deskripsi

Project ini merupakan implementasi Docker Compose untuk menjalankan WordPress dengan MySQL sebagai database dan Redis sebagai caching untuk meningkatkan performa.

---

## ⚙️ Konfigurasi

### 🔹 Environment Variables

**MySQL**

* MYSQL_DATABASE=wordpress_db
* MYSQL_USER=wordpress_user
* MYSQL_PASSWORD=wordpress_pass
* MYSQL_ROOT_PASSWORD=rootpass

**WordPress**

* WORDPRESS_DB_HOST=mysql:3306
* WORDPRESS_DB_USER=wordpress_user
* WORDPRESS_DB_PASSWORD=wordpress_pass
* WORDPRESS_DB_NAME=wordpress_db

---

### 🔹 Volume Mapping

* WordPress: /var/www/html
* MySQL: /var/lib/mysql

Digunakan agar data tetap tersimpan walaupun container dihentikan.

---

### 🔹 Network

Semua service berada dalam satu network sehingga:

* WordPress dapat mengakses MySQL melalui `mysql`
* WordPress dapat mengakses Redis melalui `redis`

---

### 🔹 Dependency

Menggunakan depends_on agar WordPress berjalan setelah MySQL.

---

## 🚀 Cara Menjalankan

1. Clone repository

```
git clone https://github.com/yudhaji11/Pemrograman-Sisi-Server.git
cd Pemrograman-Sisi-Server
```

2. Jalankan container

```
docker compose up -d
```

3. Akses WordPress

```
http://localhost:8000
```

---

## 🧠 Redis Setup

Tambahkan pada wp-config.php:

```
define('WP_REDIS_HOST', 'redis');
define('WP_REDIS_PORT', 6379);
define('WP_CACHE', true);
```

Install plugin **Redis Object Cache** lalu aktifkan.

---

## ✅ Testing

* WordPress dapat diakses
* Bisa membuat post/page
* Redis aktif (PONG)
* Data tetap ada setelah restart

---


---
Jawab Pertanyaan

1. Kenapa perlu volume untuk MySQL?
Agar data database tetap tersimpan dan tidak hilang meskipun container dihentikan atau dihapus.

2. Apa fungsi depends_on?
Untuk mengatur urutan startup container agar WordPress dijalankan setelah MySQL.

3. Bagaimana cara WordPress container connect ke MySQL?
Menggunakan environment variables dengan host berupa nama service mysql dalam network Docker.

4. Apa keuntungan pakai Redis untuk WordPress?
Untuk caching sehingga meningkatkan performa, mempercepat loading, dan mengurangi beban database.

## 📸 Screenshot
* Dashboard WordPress
  (Screenshots/wordpress.png)

* Hasil `docker ps`
  (Screenshots/terminal.png)

* Redis CLI
  (Screenshots/redis.png)

✨ Author

Yudha Aji Prasetya
