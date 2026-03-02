import React, { useContext } from 'react';
import { Trash2 } from 'lucide-react';
import { CartContext } from '../context/CartContext';

const CartItem = ({ item }) => {
    const { cart, addToCart, decrementFromCart } = useContext(CartContext);

    const qty = cart.filter(id => id === item.item_id).length;
    const itemTotal = item.price * qty;

    return (
        <div className="flex items-center justify-between p-3 md:p-4 bg-white rounded-xl shadow-sm border border-gray-100 mb-3">
            <div className="flex items-center space-x-3">
                <div className={`w-4 h-4 rounded-sm border flex items-center justify-center shrink-0 ${item.is_veg ? 'border-green-600' : 'border-red-600'}`}>
                    <div className={`w-2 h-2 rounded-full ${item.is_veg ? 'bg-green-600' : 'bg-red-600'}`}></div>
                </div>
                <div>
                    <h4 className="font-semibold text-gray-800">{item.name}</h4>
                    <p className="text-gray-500 text-xs mt-1">₹{item.price.toFixed(2)}</p>
                </div>
            </div>

            <div className="flex items-center space-x-2 sm:space-x-4">
                <div className="flex items-center shadow-sm rounded-lg overflow-hidden bg-white border border-gray-200 h-8">
                    <button onClick={() => decrementFromCart(item.item_id)} className="w-8 h-full flex items-center justify-center text-lg text-zomato font-bold hover:bg-gray-100">−</button>
                    <span className="text-sm font-bold text-zomato px-2">{qty}</span>
                    <button onClick={() => addToCart(item.item_id)} className="w-8 h-full flex items-center justify-center text-lg text-zomato font-bold hover:bg-gray-100">+</button>
                </div>
                <span className="font-bold text-gray-800 w-16 text-right">₹{itemTotal.toFixed(2)}</span>
            </div>
        </div>
    );
};

export default CartItem;
