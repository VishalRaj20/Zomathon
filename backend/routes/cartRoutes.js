import express from 'express';
import { protect } from '../middleware/authMiddleware.js';
import User from '../models/User.js';

const router = express.Router();

// Get active cart
router.get('/', protect, async (req, res) => {
    try {
        res.json(req.user.cart);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Add/Increment item in cart
router.post('/add', protect, async (req, res) => {
    try {
        const item_id = parseInt(req.body.item_id);
        const updatedUser = await User.findByIdAndUpdate(
            req.user._id,
            { $push: { cart: item_id } },
            { new: true }
        ).select('cart');
        res.json(updatedUser.cart);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Decrement single item from cart
router.post('/decrement', protect, async (req, res) => {
    try {
        const item_id = parseInt(req.body.item_id);
        const currentCart = [...req.user.cart];
        const index = currentCart.indexOf(item_id);
        if (index > -1) {
            currentCart.splice(index, 1);
        }
        const updatedUser = await User.findByIdAndUpdate(
            req.user._id,
            { $set: { cart: currentCart } },
            { new: true }
        ).select('cart');
        res.json(updatedUser.cart);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Remove item from cart
router.post('/remove', protect, async (req, res) => {
    try {
        const item_id = parseInt(req.body.item_id);
        const updatedUser = await User.findByIdAndUpdate(
            req.user._id,
            { $pull: { cart: item_id } },
            { new: true }
        ).select('cart');
        res.json(updatedUser.cart);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Clear cart
router.post('/clear', protect, async (req, res) => {
    try {
        const updatedUser = await User.findByIdAndUpdate(
            req.user._id,
            { $set: { cart: [] } },
            { new: true }
        ).select('cart');
        res.json(updatedUser.cart);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

export default router;
