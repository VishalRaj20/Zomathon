import React, { useState, useEffect, useContext } from 'react';
import api from '../api/axios';
import RestaurantCard from '../components/RestaurantCard';
import { Search, MapPin, XCircle } from 'lucide-react';
import { LocationContext } from '../context/LocationContext';

const categories = [
    { name: 'Biryani', image: 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=200&h=200&fit=crop' },
    { name: 'Pizza', image: 'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=200&h=200&fit=crop' },
    { name: 'Burger', image: 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=200&h=200&fit=crop' },
    { name: 'Healthy', image: 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=200&h=200&fit=crop' },
    { name: 'Dessert', image: 'https://images.unsplash.com/photo-1551024601-bec78aea704b?w=200&h=200&fit=crop' },
    { name: 'Chicken', image: 'https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?w=200&h=200&fit=crop' },

    {
        name: 'Pasta',
        image: 'https://images.unsplash.com/photo-1525755662778-989d0524087e?w=200&h=200&fit=crop'
    },
    {
        name: 'Sushi',
        image: 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=200&h=200&fit=crop'
    },
    {
        name: 'Ice Cream',
        image: 'https://images.unsplash.com/photo-1501443762994-82bd5dace89a?w=200&h=200&fit=crop'
    },
    {
        name: 'Sandwich',
        image: 'https://images.unsplash.com/photo-1550547660-d9450f859349?w=200&h=200&fit=crop'
    },
];


const Home = () => {
    const { location } = useContext(LocationContext);
    const [restaurants, setRestaurants] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeCategory, setActiveCategory] = useState('');
    const [dietFilter, setDietFilter] = useState('');

    useEffect(() => {
        const fetchRestaurants = async () => {
            setLoading(true);
            try {
                const params = { location };
                if (activeCategory) params.category = activeCategory.toLowerCase();
                if (dietFilter) params.diet = dietFilter;

                const { data } = await api.get('/restaurants', { params });
                setRestaurants(data);
            } catch (error) {
                console.error('Error fetching restaurants', error);
            } finally {
                setLoading(false);
            }
        };
        fetchRestaurants();
    }, [location, activeCategory, dietFilter]);

    return (
        <div className="w-full">
            {/* Hero Section */}
            <div className="relative h-[400px] mb-12 -mt-8 rounded-3xl overflow-hidden mx-auto max-w-7xl">
                <img
                    src="https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=1600&h=600&fit=crop"
                    alt="Hero Food Banner"
                    className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-black/50 flex flex-col items-center justify-center text-center px-4">
                    <h1 className="text-5xl md:text-6xl font-extrabold text-white mb-6 drop-shadow-lg">
                        Discover the best food & drinks
                    </h1>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                {/* Inspiration Section (Categories) */}
                <div className="mb-8">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-3xl font-bold text-gray-900">Inspiration for your first order</h2>
                        {activeCategory && (
                            <button
                                onClick={() => setActiveCategory('')}
                                className="flex items-center text-sm font-bold text-red-500 hover:text-red-700 transition"
                            >
                                <XCircle size={16} className="mr-1" /> Clear Filter
                            </button>
                        )}
                    </div>
                    <div className="flex overflow-x-auto hide-scrollbar space-x-6 pb-4 cursor-pointer">
                        {categories.map((cat, idx) => {
                            const isActive = activeCategory === cat.name;
                            return (
                                <div
                                    key={idx}
                                    onClick={() => setActiveCategory(cat.name === activeCategory ? '' : cat.name)}
                                    className="flex flex-col items-center space-y-3 shrink-0 group"
                                >
                                    <div className={`w-32 h-32 rounded-full overflow-hidden transition-all border-4 ${isActive ? 'border-zomato shadow-xl scale-105' : 'border-transparent group-hover:shadow-xl'}`}>
                                        <img src={cat.image} alt={cat.name} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" />
                                    </div>
                                    <span className={`font-semibold text-lg transition-colors ${isActive ? 'text-zomato' : 'text-gray-800 group-hover:text-zomato'}`}>
                                        {cat.name}
                                    </span>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Diet Filters (Veg / Non-Veg) */}
                <div className="flex items-center space-x-4 mb-8">
                    <button
                        onClick={() => setDietFilter(prev => prev === 'veg' ? '' : 'veg')}
                        className={`px-4 py-2 border rounded-full font-medium transition flex items-center shadow-sm ${dietFilter === 'veg' ? 'bg-green-50 text-green-700 border-green-500 shadow-md' : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'}`}
                    >
                        <span className="w-3 h-3 inline-block rounded-sm border border-green-600 mr-2 flex items-center justify-center p-[1px]">
                            <span className="w-full h-full bg-green-500 rounded-full"></span>
                        </span>
                        Pure Veg
                    </button>
                    <button
                        onClick={() => setDietFilter(prev => prev === 'non-veg' ? '' : 'non-veg')}
                        className={`px-4 py-2 border rounded-full font-medium transition flex items-center shadow-sm ${dietFilter === 'non-veg' ? 'bg-red-50 text-red-700 border-red-500 shadow-md' : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'}`}
                    >
                        <span className="w-3 h-3 inline-block rounded-sm border border-red-600 mr-2 flex items-center justify-center p-[1px]">
                            <span className="w-full h-full border-t-[5px] border-transparent border-b-[5px] border-b-transparent border-l-[6px] border-l-red-500 ml-1"></span>
                        </span>
                        Non-Veg
                    </button>
                </div>

                {/* Restaurant Grid */}
                <h2 className="text-3xl font-bold text-gray-900 mb-6 flex items-center">
                    Delivery Restaurants in {location}
                    {activeCategory && <span className="ml-2 text-zomato text-xl">({activeCategory})</span>}
                </h2>

                {loading ? (
                    <div className="flex items-center justify-center min-h-[30vh]">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-zomato"></div>
                    </div>
                ) : restaurants.length === 0 ? (
                    <div className="text-center py-20 text-gray-500 bg-gray-50 rounded-2xl">
                        <p className="text-xl font-semibold mb-2">No restaurants found</p>
                        <p>Try changing your location or category filter.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8 mb-20 md:mb-12">
                        {restaurants.map((rest) => (
                            <RestaurantCard key={rest.restaurant_id} restaurant={rest} />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default Home;
