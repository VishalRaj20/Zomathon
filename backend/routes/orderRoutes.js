import express from 'express';
import { protect } from '../middleware/authMiddleware.js';
import Order from '../models/Order.js';
import Item from '../models/Item.js';
import Restaurant from '../models/Restaurant.js';

const router = express.Router();

// Place a new order
router.post('/', protect, async (req, res) => {
    const { restaurant_id, items, totalAmount } = req.body;

    try {
        if (!items || items.length === 0) {
            return res.status(400).json({ message: 'No items in order' });
        }

        let actualRestaurantId = restaurant_id;
        if (!actualRestaurantId) {
            const firstItem = await Item.findOne({ item_id: items[0] });
            actualRestaurantId = firstItem ? firstItem.restaurant_id : 48;
        }

        const order = new Order({
            user: req.user._id,
            restaurant_id: actualRestaurantId,
            items,
            totalAmount,
            status: 'Preparing',
        });

        const createdOrder = await order.save();
        res.status(201).json(createdOrder);

    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Get user's past orders
router.get('/myorders', protect, async (req, res) => {
    try {
        const orders = await Order.find({ user: req.user._id }).sort({ createdAt: -1 }).lean();

        // 1. Fetch unique Items and Restaurants to enrich the payload
        const allItemIds = [...new Set(orders.flatMap(o => o.items))];
        const allRestIds = [...new Set(orders.map(o => o.restaurant_id))];

        const [allItems, allRests] = await Promise.all([
            Item.find({ item_id: { $in: allItemIds } }).lean(),
            Restaurant.find({ restaurant_id: { $in: allRestIds } }).lean()
        ]);

        const itemMap = allItems.reduce((acc, item) => ({ ...acc, [item.item_id]: item }), {});
        const restMap = allRests.reduce((acc, rest) => ({ ...acc, [rest.restaurant_id]: rest }), {});

        // Auto-advance statuses for profile view + Attach Rich metadata
        const now = Date.now();
        for (let order of orders) {
            // Check status
            const diffSeconds = (now - new Date(order.createdAt).getTime()) / 1000;
            let newStatus = order.status;
            if (diffSeconds > 45) newStatus = 'Delivered';
            else if (diffSeconds > 15) newStatus = 'Out for Delivery';

            if (order.status !== newStatus && order.status !== 'Delivered') {
                order.status = newStatus;
                try {
                    await Order.updateOne({ _id: order._id }, { $set: { status: newStatus } });
                } catch (err) { }
            }

            // Group Duplicate IDs into counts to build a clean rich item array 
            const itemCounts = {};
            order.items.forEach(id => {
                itemCounts[id] = (itemCounts[id] || 0) + 1;
            });

            order.populatedItems = Object.entries(itemCounts).map(([id, qty]) => {
                const baseItem = itemMap[id];
                return baseItem ? { ...baseItem, quantity: qty } : null;
            }).filter(Boolean);

            order.restaurant = restMap[order.restaurant_id] || { name: 'Unknown Restaurant', image_url: '' };
        }

        res.json(orders);
    } catch (error) {
        console.error('Error fetching my orders:', error);
        res.status(500).json({ message: error.message });
    }
});

// Get order status for live tracking
router.get('/:id/status', protect, async (req, res) => {
    try {
        const order = await Order.findById(req.params.id).lean();
        if (!order) return res.status(404).json({ message: 'Order not found' });
        if (order.user.toString() !== req.user._id.toString()) return res.status(401).json({ message: 'Not authorized' });

        const diffSeconds = (Date.now() - new Date(order.createdAt).getTime()) / 1000;
        let newStatus = order.status;

        if (diffSeconds > 45) {
            newStatus = 'Delivered';
        } else if (diffSeconds > 15) {
            newStatus = 'Out for Delivery';
        } else if (order.status === 'Pending' || !order.status) {
            newStatus = 'Preparing';
        }

        if (order.status !== newStatus) {
            try {
                await Order.updateOne({ _id: order._id }, { $set: { status: newStatus } });
            } catch (err) { }
        }

        res.json({ status: newStatus, estimatedDelivery: '15-20 mins' });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Get order by ID for tracking
router.get('/:id', protect, async (req, res) => {
    try {
        const order = await Order.findById(req.params.id).lean();
        if (!order) {
            return res.status(404).json({ message: 'Order not found' });
        }

        // Ensure the user owns this order
        if (order.user.toString() !== req.user._id.toString()) {
            return res.status(401).json({ message: 'Not authorized to view this order' });
        }

        // Auto-advance status for hackathon demo purposes
        const diffSeconds = (Date.now() - new Date(order.createdAt).getTime()) / 1000;
        let newStatus = order.status;

        if (diffSeconds > 45) {
            newStatus = 'Delivered';
        } else if (diffSeconds > 15) {
            newStatus = 'Out for Delivery';
        } else if (order.status === 'Pending' || !order.status) {
            newStatus = 'Preparing';
        }

        if (order.status !== newStatus) {
            order.status = newStatus;
            try {
                await Order.updateOne({ _id: order._id }, { $set: { status: newStatus } });
            } catch (err) {
                // Ignore
            }
        }

        res.json(order);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

export default router;
