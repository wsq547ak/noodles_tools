module.exports = {
  apps: [
    {
      name: "tools",
      cwd: __dirname,
      script: "./apps/web/.next/standalone/apps/web/server.js",
      env: {
        HOSTNAME: "127.0.0.1",
        NODE_ENV: "production",
        PORT: 4001,
      },
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
    },
    {
      name: "piczip_server",
      cwd: __dirname,
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
    {
      name: "random_stu_server",
      cwd: __dirname,
      script: "python3",
      args: "-m services.randomStu.server",
      env: {
        RANDOMSTU_HOST: "127.0.0.1",
        RANDOMSTU_PORT: 5002,
      },
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "300M",
    },
  ],
};
