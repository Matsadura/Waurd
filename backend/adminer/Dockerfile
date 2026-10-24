FROM debian:12

# Install php-cli, curl/wget, and the MySQL driver
RUN apt update && apt install -y php-cli php-mysql wget && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /var/www/html

RUN wget https://github.com/vrana/adminer/releases/download/v4.8.1/adminer-4.8.1.php -O index.php

EXPOSE 8080

# Start PHP built-in web server on 0.0.0.0:8080
CMD ["php", "-S", "0.0.0.0:8080", "-t", "/var/www/html"]