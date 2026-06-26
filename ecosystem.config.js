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
  ],
};
