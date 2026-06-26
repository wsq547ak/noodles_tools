module.exports = {
  apps: [
    {
      name: "tools",
      script: "./apps/web/.next/standalone/apps/web/server.js",
      env: {
        NODE_ENV: "production",
        PORT: 4001,
      },
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
    },
    {
      name: "tools_server",
      script: "python3",
      args: "-m services.picZip.server",
      env: {
        PICZIP_HOST: "127.0.0.1",
        PICZIP_PORT: 5001,
      },
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "500M",
    },
  ],
};
