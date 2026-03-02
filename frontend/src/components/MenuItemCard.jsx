import React, { useContext } from 'react';
import { Plus, Check } from 'lucide-react';
import { CartContext } from '../context/CartContext';

const MenuItemCard = ({ item }) => {
    const { cart, addToCart, decrementFromCart } = useContext(CartContext);

    const qty = cart.filter(id => id === item.item_id).length;

    return (
        <div className="flex justify-between items-center p-4 border-b border-gray-100 hover:bg-gray-50 transition-colors">
            <div className="flex-1 pr-4">
                <div className="flex items-center space-x-2 mb-1">
                    <div className={`w-4 h-4 rounded-sm border flex items-center justify-center ${item.is_veg ? 'border-green-600' : 'border-red-600'}`}>
                        <div className={`w-2 h-2 rounded-full ${item.is_veg ? 'bg-green-600' : 'bg-red-600'}`}></div>
                    </div>
                    <h4 className="font-semibold text-gray-800 text-lg">{item.name}</h4>
                </div>
                <p className="text-gray-800 font-medium">₹{item.price.toFixed(2)}</p>
                <p className="text-gray-500 text-sm mt-1 capitalize">{item.category}</p>
            </div>

            <div className="relative">
                <div className="w-24 h-24 bg-gray-200 rounded-xl overflow-hidden mb-4">
                    <img
                        src={`https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=200&q=80`}
                        alt={item.name}
                        className="w-full h-full object-cover"
                    />
                </div>

                <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 shadow-md rounded-lg overflow-hidden bg-white border border-gray-200 flex items-center h-9">
                    {qty === 0 ? (
                        <button
                            onClick={() => addToCart(item.item_id)}
                            className="px-6 py-1.5 w-full h-full font-bold text-sm text-zomato hover:bg-gray-50 transition-colors"
                        >
                            ADD
                        </button>
                    ) : (
                        <div className="flex items-center w-full h-full justify-between px-2 text-zomato font-bold min-w-[80px]">
                            <button onClick={() => decrementFromCart(item.item_id)} className="w-6 h-full flex items-center justify-center text-lg hover:bg-gray-100">−</button>
                            <span className="text-sm">{qty}</span>
                            <button onClick={() => addToCart(item.item_id)} className="w-6 h-full flex items-center justify-center text-lg hover:bg-gray-100">+</button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default MenuItemCard;
