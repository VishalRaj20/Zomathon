import React, { useContext } from 'react';
import { Plus, Check, Sparkles } from 'lucide-react';
import { CartContext } from '../context/CartContext';

const RecommendationCard = ({ item }) => {
    const { cart, addToCart } = useContext(CartContext);
    const inCart = cart.includes(item.item_id);

    return (
        <div className="bg-gradient-to-br from-orange-50 to-red-50 rounded-2xl p-3 sm:p-4 shadow-sm border border-red-100 flex items-center justify-between hover:shadow-md transition-all relative overflow-hidden group">
            {/* Decorative background element */}
            <div className="absolute -right-6 -top-6 text-red-100 opacity-50 group-hover:scale-110 transition-transform hidden sm:block">
                <Sparkles size={100} />
            </div>

            <div className="flex items-center space-x-3 sm:space-x-4 relative z-10 w-full">
                <div className="w-14 h-14 sm:w-16 sm:h-16 bg-white rounded-xl overflow-hidden shadow-sm shrink-0 border border-red-50">
                    <img
                        src={`https://source.unsplash.com/150x150/?${item.category},${item.name.split(' ')[0]}`}
                        alt={item.name}
                        className="w-full h-full object-cover"
                        onError={(e) => { e.target.src = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=150&q=80" }}
                    />
                </div>

                <div className="flex-1">
                    <div className="flex items-center space-x-2">
                        <div className={`w-3 h-3 rounded-sm border flex items-center justify-center ${item.is_veg ? 'border-green-600' : 'border-red-600'}`}>
                            <div className={`w-1.5 h-1.5 rounded-full ${item.is_veg ? 'bg-green-600' : 'bg-red-600'}`}></div>
                        </div>
                        <h4 className="font-bold text-gray-800 line-clamp-1">{item.name}</h4>
                    </div>
                    <p className="text-gray-500 text-xs capitalize mt-0.5">{item.category}</p>
                    <p className="font-semibold text-zomato mt-1">₹{item.price.toFixed(2)}</p>
                </div>

                <button
                    onClick={() => addToCart(item.item_id)}
                    disabled={inCart}
                    className={`shrink-0 flex items-center justify-center rounded-full p-2 transition-colors ${inCart
                        ? 'bg-green-100 text-green-600'
                        : 'bg-white text-zomato hover:bg-zomato hover:text-white shadow-sm border border-red-100'
                        }`}
                >
                    {inCart ? <Check size={20} /> : <Plus size={20} />}
                </button>
            </div>
        </div>
    );
};

export default RecommendationCard;
