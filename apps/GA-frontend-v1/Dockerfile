#使用nginx作为基础镜像
FROM nginx:1.28.0

# 将本地nginx.conf拷贝到容器中的/etc/nginx/conf.d/目录

COPY mcp_client.conf /etc/nginx/conf.d/default.conf


# 将本地的dist文件夹拷贝到容器中的/usr/share/nginx/html目录

COPY dist/ /usr/share/nginx/html