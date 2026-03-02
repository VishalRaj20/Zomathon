const http = require('http');
const jwt = require('jsonwebtoken');
const mongoose = require('mongoose');

mongoose.connect('mongodb://127.0.0.1:27017/zomathon').then(async () => {
    const user = await mongoose.connection.collection('users').findOne({ email: 'test@test.com' });
    const token = jwt.sign({ id: user._id.toString() }, 'supersecretjwtkey_for_hackathon_only', { expiresIn: '30d' });

    console.log("Token generated:", token);

    const opts = {
        hostname: '127.0.0.1',
        port: 5000,
        path: '/api/orders/myorders',
        method: 'GET',
        headers: {
            Authorization: `Bearer ${token}`
        }
    };

    const req = http.request(opts, res => {
        let data = '';
        res.on('data', d => data += d);
        res.on('end', () => {
            console.log('STATUS:', res.statusCode);
            console.log('BODY:', data);
            process.exit(0);
        });
    });

    req.on('error', e => {
        console.error(e);
        process.exit(1);
    });

    req.end();
});
