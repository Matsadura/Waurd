FROM node:24-alpine

WORKDIR /frontend_inside_container

COPY entrypoint.sh /entrypoint.sh

EXPOSE 5173

ENTRYPOINT ["sh", "/entrypoint.sh"]

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]