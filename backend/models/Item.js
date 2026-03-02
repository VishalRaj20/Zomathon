import mongoose from 'mongoose';

const itemSchema = mongoose.Schema(
    {
        item_id: { type: Number, required: true, unique: true },
        restaurant_id: { type: Number, required: true },
        name: { type: String, required: true },
        category: { type: String, required: true },
        price: { type: Number, required: true },
        is_veg: { type: Number, required: true },
        image_url: { type: String }
    },
    {
        timestamps: true,
        toJSON: { virtuals: true },
        toObject: { virtuals: true }
    }
);

// Virtual for populating restaurant details since restaurant_id is a custom Number, not an ObjectId
itemSchema.virtual('restaurant', {
    ref: 'Restaurant',
    localField: 'restaurant_id',
    foreignField: 'restaurant_id',
    justOne: true
});

itemSchema.index({ name: 'text', category: 'text' });

export default mongoose.model('Item', itemSchema);
