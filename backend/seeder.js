import mongoose from 'mongoose';
import fs from 'fs';
import path from 'path';
import 'dotenv/config';

import Restaurant from './models/Restaurant.js';
import Item from './models/Item.js';
import connectDB from './config/db.js';

// Extremely basic CSV parser for the hackathon
const parseCSV = (filepath) => {
    const content = fs.readFileSync(filepath, 'utf8');
    const lines = content.split('\n').filter(l => l.trim().length > 0);
    const headers = lines[0].split(',');

    return lines.slice(1).map(line => {
        const values = line.split(',');
        const obj = {};
        headers.forEach((h, i) => obj[h.trim()] = values[i]?.trim());
        return obj;
    });
};

const importData = async () => {
    try {
        await connectDB();

        // Clear existing
        await Restaurant.deleteMany();
        await Item.deleteMany();
        console.log('MongoDB Cleared!');

        // Import Restaurants (just the first 20 for UI speed)
        const rests = parseCSV('../data/raw/restaurants.csv').slice(0, 20);
        const mappedRests = rests.map(r => ({
            restaurant_id: parseInt(r.restaurant_id),
            name: r.name,
            cuisine: r.cuisine,
            rating: parseFloat(r.rating) || 4.0
        }));
        await Restaurant.insertMany(mappedRests);
        console.log('Restaurants Imported!');

        // Import Items for those 20 restaurants
        const items = parseCSV('../data/raw/items.csv');
        const validRestIds = new Set(mappedRests.map(r => r.restaurant_id));
        const mappedItems = items
            .filter(i => validRestIds.has(parseInt(i.restaurant_id)))
            .map(i => ({
                item_id: parseInt(i.item_id),
                restaurant_id: parseInt(i.restaurant_id),
                name: i.name,
                category: i.category,
                price: parseFloat(i.price),
                is_veg: parseInt(i.is_veg)
            }));

        await Item.insertMany(mappedItems);
        console.log('Items Imported!');

        process.exit();
    } catch (error) {
        console.error(`Error: ${error.message}`);
        process.exit(1);
    }
};

importData();
