import mongoose from 'mongoose';

const restaurantSchema = mongoose.Schema(
    {
        restaurant_id: { type: Number, required: true, unique: true },
        name: { type: String, required: true },
        cuisine: { type: String, required: true },
        rating: { type: Number, required: true },
        image_url: { type: String },
        city: { type: String, default: 'Bangalore' }
    },
    { timestamps: true }
);

restaurantSchema.index({ name: 'text', cuisine: 'text', city: 'text' });

export default mongoose.model('Restaurant', restaurantSchema);
