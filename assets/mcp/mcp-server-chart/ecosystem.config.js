module.exports = {
  apps: [
    {
      name: 'gpt-vis-ssr',
      script: 'npm',
      args: ['run', 'dev'],
      watch: false,
      output: './logs/gpt-vis-ssr-out.log',
      error: './logs/gpt-vis-ssr-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },
    {
      name: 'mcp-server-chart',
      script: 'mcp-server-chart',
      args: '--transport sse',
      watch: false,
      output: './logs/mcp-server-chart-out.log',
      error: './logs/mcp-server-chart-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },
  ],
};

