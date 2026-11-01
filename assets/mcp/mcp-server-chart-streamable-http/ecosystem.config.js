module.exports = {
  apps: [
    {
      name: 'gpt-vis-ssr',
      script: 'npm',
      args: ['run', 'dev'],
      env_file: '.env',
      env: {
        RENDER_PORT: process.env.RENDER_PORT || '8999',
      },
      watch: false,
      output: './logs/gpt-vis-ssr-out.log',
      error: './logs/gpt-vis-ssr-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },
    {
      name: 'mcp-server-chart',
      script: 'mcp-server-chart',
      env_file: '.env',
      args: [
        '--transport',
        'streamable',
        '--port',
        process.env.MCP_PORT || '1122',
        '--endpoint',
        process.env.MCP_ENDPOINT || '/mcp',
      ],
      env: {
        HOST: process.env.MCP_HOST || '0.0.0.0',
        VIS_REQUEST_SERVER: process.env.VIS_REQUEST_SERVER || 'http://127.0.0.1:8999/render-chart',
        COMPATIBILITY_MODE: process.env.COMPATIBILITY_MODE || 'true',
        SERVICE_ID: process.env.SERVICE_ID || '',
        DISABLED_TOOLS: process.env.DISABLED_TOOLS || '',
      },
      watch: false,
      output: './logs/mcp-server-chart-out.log',
      error: './logs/mcp-server-chart-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },
  ],
};
