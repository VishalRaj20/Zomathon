import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Star } from 'lucide-react';
import api from '../api/axios';
import MenuItemCard from '../components/MenuItemCard';

const Restaurant = () => {
    const { id } = useParams();
    const [restaurant, setRestaurant] = useState(null);
    const [menu, setMenu] = useState([]);
    const [categories, setCategories] = useState(['All']);
    const [activeCategory, setActiveCategory] = useState('All');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchMenu = async () => {
            try {
                const { data } = await api.get(`/restaurants/${id}`);
                setRestaurant(data.restaurant);
                setMenu(data.menu);

                // Extract unique categories
                const uniqueCats = ['All', ...new Set(data.menu.map(item => item.category))];
                setCategories(uniqueCats);
            } catch (error) {
                console.error('Error fetching menu', error);
            } finally {
                setLoading(false);
            }
        };
        fetchMenu();
    }, [id]);

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-zomato"></div>
            </div>
        );
    }

    if (!restaurant) return <div className="text-center mt-20 text-gray-600">Restaurant not found</div>;

    return (
        <div className="max-w-4xl mx-auto bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden mb-12">
            {/* Restaurant Header */}
            <div className="relative h-64 bg-gray-900">
                <img
                    src={`https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1200&h=400&fit=crop`}
                    alt={restaurant.name}
                    className="w-full h-full object-cover opacity-60"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent"></div>
                <div className="absolute bottom-6 left-6 right-6">
                    <h1 className="text-4xl font-bold text-white mb-2">{restaurant.name}</h1>
                    <div className="flex items-center text-gray-200 space-x-4">
                        <span className="text-lg">{restaurant.cuisine}</span>
                        <span className="flex items-center bg-green-600 text-white px-2 py-0.5 rounded text-sm font-bold">
                            {restaurant.rating} <Star size={14} className="ml-1" fill="currentColor" />
                        </span>
                    </div>
                </div>
            </div>

            {/* Menu List */}
            <div className="p-6">
                <h3 className="text-2xl font-bold text-gray-800 mb-6 flex items-center space-x-2">
                    <span>Order Online</span>
                </h3>

                {/* Category Filters */}
                <div className="flex overflow-x-auto hide-scrollbar space-x-3 mb-8 pb-2">
                    {categories.map(cat => (
                        <button
                            key={cat}
                            onClick={() => setActiveCategory(cat)}
                            className={`whitespace-nowrap px-4 py-2 rounded-full font-medium transition-colors border ${activeCategory === cat
                                ? 'bg-red-50 text-zomato border-red-200 shadow-sm'
                                : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                                }`}
                        >
                            <span className="capitalize">{cat}</span>
                        </button>
                    ))}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-0">
                    {menu
                        .filter(item => activeCategory === 'All' || item.category === activeCategory)
                        .map((item) => (
                            <MenuItemCard key={item.item_id} item={item} />
                        ))}
                </div>
            </div>
        </div>
    );
};

export default Restaurant;
