import express from 'express';
import Restaurant from '../models/Restaurant.js';
import Item from '../models/Item.js';

const router = express.Router();

// GET all restaurants with optional location and category filters
router.get('/', async (req, res) => {
    try {
        const { location, category } = req.query;
        let query = {};

        if (location) {
            query.city = new RegExp(location, 'i');
        }

        if (category) {
            // Find items matching this category term in their NAME (e.g. finding "Chicken" in "Butter Chicken")
            const items = await Item.find({ name: new RegExp(category, 'i') });
            const restaurantIds = [...new Set(items.map(item => item.restaurant_id))];

            // Match restaurants that either have this cuisine OR serve items containing this word
            query.$or = [
                { cuisine: new RegExp(category, 'i') },
                { restaurant_id: { $in: restaurantIds } }
            ];
        }

        let finalQuery = query;

        const { diet } = req.query;
        if (diet) {
            // If veg: we want PURE veg restaurants (no non-veg items).
            // If non-veg: we want restaurants that serve at least one non-veg item.
            const nonVegItems = await Item.find({ is_veg: 0 });
            const nonVegRestIds = [...new Set(nonVegItems.map(i => i.restaurant_id))];

            if (diet === 'veg') {
                if (finalQuery.$or) {
                    finalQuery = { $and: [finalQuery, { restaurant_id: { $nin: nonVegRestIds } }] };
                } else {
                    finalQuery.restaurant_id = { $nin: nonVegRestIds };
                }
            } else if (diet === 'non-veg') {
                if (finalQuery.$or) {
                    finalQuery = { $and: [finalQuery, { restaurant_id: { $in: nonVegRestIds } }] };
                } else {
                    finalQuery.restaurant_id = { $in: nonVegRestIds };
                }
            }
        }

        const restaurants = await Restaurant.find(finalQuery);
        res.json(restaurants);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// GET single restaurant and its menu
router.get('/:id', async (req, res) => {
    try {
        const restaurant = await Restaurant.findOne({ restaurant_id: req.params.id });
        if (!restaurant) return res.status(404).json({ message: 'Restaurant not found' });

        const items = await Item.find({ restaurant_id: req.params.id });
        res.json({ restaurant, menu: items });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

export default router;
