import React, { useState, useEffect, useContext, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShoppingCart, LogOut, User, Search, MapPin } from 'lucide-react';
import { AuthContext } from '../context/AuthContext';
import { CartContext } from '../context/CartContext';
import { LocationContext } from '../context/LocationContext';
import api from '../api/axios';

const ALL_CITIES = [
    "Bangalore", "Mumbai", "Delhi", "Hyderabad", "Chennai", "Kolkata",
    "Pune", "Ahmedabad", "Jaipur", "Chandigarh", "Lucknow", "Kanpur",
    "Nagpur", "Indore", "Bhopal", "Visakhapatnam", "Patna", "Vadodara",
    "Ghaziabad", "Ludhiana", "Agra", "Nashik", "Faridabad", "Meerut",
    "Rajkot", "Kalyan", "Vasai-Virar", "Varanasi", "Srinagar", "Aurangabad"
];

const Navbar = () => {
    const { user, logout } = useContext(AuthContext);
    const { cart, clearCart } = useContext(CartContext);
    const { location, setLocation } = useContext(LocationContext);
    const navigate = useNavigate();

    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState({ restaurants: [], items: [] });
    const [showResults, setShowResults] = useState(false);
    const searchRef = useRef(null);

    const handleLocationChange = (e) => {
        const newCity = e.target.value;
        if (newCity !== location) {
            setLocation(newCity);
            if (clearCart) clearCart();
            localStorage.removeItem('cart');
            navigate('/');
        }
    };

    const handleLogout = () => {
        logout();
        navigate('/');
    };

    // Close dropdown on outside click
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (searchRef.current && !searchRef.current.contains(event.target)) {
                setShowResults(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Debounced Search
    useEffect(() => {
        const delayDebounceFn = setTimeout(async () => {
            if (searchQuery.length >= 2) {
                try {
                    const { data } = await api.get(`/search?q=${searchQuery}&location=${location}`);
                    setSearchResults(data);
                    setShowResults(true);
                } catch (err) {
                    console.error('Search failed', err);
                }
            } else {
                setSearchResults({ restaurants: [], items: [] });
                setShowResults(false);
            }
        }, 300);

        return () => clearTimeout(delayDebounceFn);
    }, [searchQuery, location]);

    const handleResultClick = (path) => {
        setShowResults(false);
        setSearchQuery('');
        navigate(path);
    };

    const searchResultsDropdownContent = (
        <>
            {searchResults.restaurants.length > 0 && (
                <div className="mb-2">
                    <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider px-3 py-1">Restaurants</h4>
                    {searchResults.restaurants.map(rest => (
                        <div
                            key={rest.restaurant_id}
                            onClick={() => handleResultClick(`/restaurant/${rest.restaurant_id}`)}
                            className="px-3 py-2 hover:bg-red-50 cursor-pointer rounded-lg flex items-center space-x-3 transition-colors"
                        >
                            <div className="w-10 h-10 rounded-lg bg-gray-100 overflow-hidden shrink-0">
                                <img src={rest.image_url || `https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=100&q=80`} alt={rest.name} className="w-full h-full object-cover" />
                            </div>
                            <div>
                                <div className="font-semibold text-gray-800 text-sm">{rest.name}</div>
                                <div className="text-xs text-gray-500">{rest.cuisine} • {rest.city}</div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
            {searchResults.items.length > 0 && (
                <div>
                    <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider px-3 py-1">Dishes</h4>
                    {searchResults.items.map(item => (
                        <div
                            key={item.item_id}
                            onClick={() => handleResultClick(`/restaurant/${item.restaurant?.restaurant_id || item.restaurant_id}`)}
                            className="px-3 py-2 hover:bg-red-50 cursor-pointer rounded-lg flex items-center space-x-3 transition-colors"
                        >
                            <div className="w-10 h-10 rounded-lg bg-gray-100 overflow-hidden shrink-0">
                                <img src={item.image_url || `https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=100&q=80`} alt={item.name} className="w-full h-full object-cover" />
                            </div>
                            <div>
                                <div className="font-semibold text-gray-800 text-sm">{item.name} <span className="text-xs text-gray-500 font-normal ml-1">in {item.restaurant?.name || 'Restaurant'}</span></div>
                                <div className="text-xs text-gray-500 capitalize">{item.category} • ₹{item.price}</div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </>
    );

    return (
        <nav ref={searchRef} className="bg-white shadow-md sticky top-0 z-50">
            <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                <Link to="/" className="text-2xl font-bold text-zomato tracking-tighter shrink-0">
                    zomathon
                </Link>

                {/* Global Search Bar (Desktop) */}
                <div className="hidden md:flex flex-1 max-w-3xl lg:max-w-4xl mx-8 relative">
                    <div className="flex w-full h-12 border border-gray-200 rounded-xl shadow-sm bg-white overflow-hidden focus-within:shadow-md focus-within:border-gray-300 transition-all">
                        <div className="flex items-center space-x-2 px-4 bg-white w-1/3 hover:bg-gray-50 transition-colors border-r border-gray-200 shrink-0">
                            <MapPin className="text-zomato shrink-0 ml-1" size={20} />
                            <select
                                value={location}
                                onChange={handleLocationChange}
                                className="w-full text-base text-gray-700 outline-none bg-transparent appearance-none cursor-pointer pl-1 pr-2 py-1"
                            >
                                {ALL_CITIES.map(city => (
                                    <option key={city} value={city} className="py-2 pl-2">{city}</option>
                                ))}
                            </select>
                        </div>
                        <div className="flex items-center w-2/3 px-4">
                            <Search className="text-gray-400 shrink-0 mr-3" size={20} />
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={(e) => {
                                    setSearchQuery(e.target.value);
                                    if (e.target.value.length > 0) setShowResults(true);
                                }}
                                onFocus={() => searchQuery.length >= 2 && setShowResults(true)}
                                placeholder="Search for restaurant, cuisine or a dish"
                                className="w-full text-base outline-none bg-transparent"
                            />
                        </div>
                    </div>

                    {/* Search Results Dropdown (Desktop) */}
                    {showResults && (searchResults.restaurants.length > 0 || searchResults.items.length > 0) && (
                        <div className="absolute top-14 left-0 w-full bg-white rounded-xl shadow-xl border border-gray-100 p-2 z-50 max-h-[400px] overflow-y-auto">
                            {searchResultsDropdownContent}
                        </div>
                    )}
                </div>

                <div className="flex items-center space-x-4 md:space-x-6 shrink-0">
                    {user ? (
                        <>
                            <Link to="/profile" className="flex items-center space-x-2 text-gray-700 hover:text-zomato transition-colors">
                                {user.avatar ? (
                                    <img src={user.avatar} className="w-8 h-8 rounded-full border border-gray-200 object-cover" alt="Avatar" />
                                ) : (
                                    <User size={20} />
                                )}
                                <span className="font-medium hidden sm:inline">{user.name.split(' ')[0]}</span>
                            </Link>

                            <Link to="/cart" className="relative text-gray-700 hover:text-zomato transition-colors">
                                <ShoppingCart size={24} />
                                {cart.length > 0 && (
                                    <span className="absolute -top-2 -right-2 bg-zomato text-white text-xs font-bold rounded-full h-5 w-5 flex items-center justify-center">
                                        {cart.length}
                                    </span>
                                )}
                            </Link>

                            <button
                                onClick={handleLogout}
                                className="flex items-center space-x-1 text-gray-400 hover:text-red-500 transition-colors"
                                title="Logout"
                            >
                                <LogOut size={20} />
                            </button>
                        </>
                    ) : (
                        <div className="space-x-4">
                            <Link to="/login" className="text-gray-600 hover:text-gray-900 font-medium">Login</Link>
                            <Link to="/register" className="bg-zomato text-white px-4 py-2 rounded-lg font-medium hover:bg-red-600 transition-colors">
                                Sign Up
                            </Link>
                        </div>
                    )}
                </div>
            </div>

            {/* Mobile Location/Search (Optional simpler version) */}
            <div className="md:hidden px-4 pb-3 flex space-x-2 relative">
                <select
                    value={location}
                    onChange={handleLocationChange}
                    className="w-1/3 border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none bg-white"
                >
                    {ALL_CITIES.map(city => (
                        <option key={city} value={city} className="py-2 pl-2">{city}</option>
                    ))}
                </select>
                <div className="flex-1 relative border border-gray-200 rounded-lg bg-gray-50 px-2 py-1.5 flex items-center">
                    <Search size={14} className="text-gray-400 mr-2 shrink-0" />
                    <input type="text" placeholder="Search..." className="w-full text-sm bg-transparent outline-none" value={searchQuery} onChange={(e) => { setSearchQuery(e.target.value); if (e.target.value.length > 0) setShowResults(true); }} onFocus={() => searchQuery.length >= 2 && setShowResults(true)} />
                </div>

                {/* Search Results Dropdown (Mobile) */}
                {showResults && (searchResults.restaurants.length > 0 || searchResults.items.length > 0) && (
                    <div className="absolute top-full mt-1 left-4 right-4 bg-white rounded-xl shadow-[0_10px_40px_rgba(0,0,0,0.15)] border border-gray-100 p-2 z-[60] max-h-[60vh] overflow-y-auto">
                        {searchResultsDropdownContent}
                    </div>
                )}
            </div>
        </nav>
    );
};

export default Navbar;
