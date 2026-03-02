import mongoose from 'mongoose';

const orderSchema = mongoose.Schema(
    {
        user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
        restaurant_id: { type: Number, required: true },
        items: [{ type: Number }], // Array of item_ids
        totalAmount: { type: Number, required: true },
        status: { type: String, default: 'Preparing' }
    },
    { timestamps: true }
);

export default mongoose.model('Order', orderSchema);
