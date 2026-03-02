import express from 'express';
import axios from 'axios';
import { protect } from '../middleware/authMiddleware.js';
import Item from '../models/Item.js';

const router = express.Router();

router.post('/', async (req, res) => {
    const { timestamp, top_k, cart_items, city } = req.body;

    try {
        // Allow empty cart recommendations
        let cartItemsToPass = [];

        // Pass 0 instead of taking 300ms to query Atlas for the Restaurant ID! 
        // Python handles this instantly from Memory now.
        let actualRestaurantId = 0;

        if (cart_items && cart_items.length > 0) {
            cartItemsToPass = cart_items.map(id => parseInt(id));
        } else if (req?.user?.cart?.length > 0) {
            cartItemsToPass = req.user.cart.map(id => parseInt(id));
        }

        const payload = {
            user_id: 27,
            restaurant_id: parseInt(actualRestaurantId),
            cart_items: cartItemsToPass,
            top_k: parseInt(top_k) || 5,
            timestamp: timestamp,
            city: city || ''
        };

        const mlServiceUrl = process.env.ML_SERVICE_URL || 'http://127.0.0.1:8000/recommend';

        // Forward to FastAPI
        const response = await axios.post(mlServiceUrl, payload);
        res.json(response.data);

    } catch (error) {
        console.error('ML Service Error:', error.message);
        res.status(500).json({ message: 'Error retrieving recommendations from ML service' });
    }
});

export default router;
