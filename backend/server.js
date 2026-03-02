import express from 'express';
import cors from 'cors';
import 'dotenv/config';
import connectDB from './config/db.js';

import authRoutes from './routes/authRoutes.js';
import restaurantRoutes from './routes/restaurantRoutes.js';
import cartRoutes from './routes/cartRoutes.js';
import recommendRoutes from './routes/recommendRoutes.js';
import orderRoutes from './routes/orderRoutes.js';
import searchRoutes from './routes/searchRoutes.js';

connectDB();

const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.use('/api/auth', authRoutes);
app.use('/api/restaurants', restaurantRoutes);
app.use('/api/cart', cartRoutes);
app.use('/api/recommend', recommendRoutes);
app.use('/api/orders', orderRoutes);
app.use('/api/search', searchRoutes);

// Error Handling Middleware
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ message: err.message || 'Internal Server Error' });
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`Backend Server running on port ${PORT}`));
