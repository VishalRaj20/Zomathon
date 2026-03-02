import React from 'react';
import { Link } from 'react-router-dom';
import { Star } from 'lucide-react';

const RestaurantCard = ({ restaurant }) => {
    return (
        <Link to={`/restaurant/${restaurant.restaurant_id}`} className="group">
            <div className="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 border border-gray-100 flex flex-col h-full">
                {/* Placeholder image since we don't have real images */}
                <div className="h-48 bg-gray-200 relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent z-10"></div>
                    <img
                        src={`https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800&q=80`}
                        alt={restaurant.name}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        onError={(e) => {
                            e.target.src = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800&q=80";
                        }}
                    />
                    <div className="absolute bottom-3 left-3 z-20">
                        <h3 className="text-xl font-bold text-white mb-1">{restaurant.name}</h3>
                    </div>
                </div>

                <div className="p-4 flex-grow flex flex-col justify-between">
                    <div className="flex justify-between items-start mb-2">
                        <p className="text-gray-500 text-sm truncate pr-2">{restaurant.cuisine}</p>
                        <div className="flex items-center space-x-1 bg-green-600 text-white px-2 py-1 rounded text-xs font-bold">
                            <span>{restaurant.rating}</span>
                            <Star size={12} fill="currentColor" />
                        </div>
                    </div>
                </div>
            </div>
        </Link>
    );
};

export default RestaurantCard;
