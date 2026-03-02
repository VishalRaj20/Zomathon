import mongoose from 'mongoose';
import Order from './models/Order.js';
import Item from './models/Item.js';
import Restaurant from './models/Restaurant.js';

mongoose.connect('mongodb://localhost:27017/zomathon').then(async () => {
    const allItemIds = [1, 6];
    const allRestIds = [1];

    const allItems = await Item.find({ item_id: { $in: allItemIds } }).lean();
    const allRests = await Restaurant.find({ restaurant_id: { $in: allRestIds } }).lean();

    console.log("Items query res:", allItems);
    console.log("Rests query res:", allRests);

    const firstOrder = await Order.findOne({ restaurant_id: 1 }).lean();
    console.log("First Order:", firstOrder);

    process.exit();
});
