const http = require('http');
http.get('http://127.0.0.1:3000/', (res) => {
  console.log('STATUS', res.statusCode);
  process.exit(0);
}).on('error', (err) => {
  console.error('ERROR', err.message);
  process.exit(1);
});
