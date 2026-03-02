import express from 'express';
import Restaurant from '../models/Restaurant.js';
import Item from '../models/Item.js';

const router = express.Router();

router.get('/', async (req, res) => {
    const { q, location } = req.query;
    if (!q) return res.json({ restaurants: [], items: [] });
    if (!location) return res.status(400).json({ message: "Location is required for search" });

    try {
        // Find restaurants matching the query AND located in the specified city
        const queryFilter = {
            city: location,
            $text: { $search: q }
        };

        // 1: Find all restaurants in the given city to get their IDs
        const localRestaurants = await Restaurant.find({ city: location }).select('restaurant_id -_id');
        const localRestaurantIds = localRestaurants.map(r => r.restaurant_id);

        try {
            const restaurants = await Restaurant.find(
                queryFilter,
                { score: { $meta: "textScore" } }
            ).sort({ score: { $meta: "textScore" } }).limit(10);

            // Fetch items that text-match AND belong to a restaurant in this city
            const items = await Item.find(
                {
                    restaurant_id: { $in: localRestaurantIds },
                    $text: { $search: q }
                },
                { score: { $meta: "textScore" } }
            ).sort({ score: { $meta: "textScore" } }).populate('restaurant').limit(20);

            if (restaurants.length === 0 && items.length === 0) {
                throw new Error("Fallback to regex for partial match");
            }
            res.json({ restaurants, items });

        } catch (textError) {
            const regex = new RegExp(q, 'i');

            const restaurants = await Restaurant.find({
                city: location,
                $or: [{ name: regex }, { cuisine: regex }]
            }).limit(10);

            // Fetch items that regex-match AND belong to a restaurant in this city
            const items = await Item.find({
                restaurant_id: { $in: localRestaurantIds },
                $or: [{ name: regex }, { category: regex }]
            }).populate('restaurant').limit(20);

            res.json({ restaurants, items });
        }
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

export default router;
