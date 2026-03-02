import React, { useState, useEffect, useContext, useRef } from 'react';
import { ChefHat, MapPin, Phone, Mail, Clock, ChevronRight, Edit2, Check, X, Search, Filter } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '../api/axios';
import { AuthContext } from '../context/AuthContext';

const Profile = () => {
    const { user, updateProfile } = useContext(AuthContext);
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [statusFilter, setStatusFilter] = useState('All');
    const prevStatusesRef = useRef({});

    const statusToMap = {
        'Preparing': 1,
        'Out for Delivery': 2,
        'Delivered': 3
    };

    const [isEditing, setIsEditing] = useState(false);
    const [formData, setFormData] = useState({
        name: user?.name || '',
        phone: user?.phone || '',
        address: user?.address || '',
        avatar: user?.avatar || ''
    });

    useEffect(() => {
        if (user) {
            setFormData({
                name: user.name || '',
                phone: user.phone || '',
                address: user.address || '',
                avatar: user.avatar || ''
            });
        }
    }, [user]);

    const handleUpdateProfile = async (e) => {
        e.preventDefault();
        try {
            await updateProfile(formData);
            setIsEditing(false);
        } catch (error) {
            console.error('Failed to update profile', error);
            alert('Failed to update profile. Please try again.');
        }
    };

    useEffect(() => {
        let isMounted = true;
        const fetchOrders = async () => {
            try {
                const { data } = await api.get('/orders/myorders');

                let shouldPlaySound = false;
                data.forEach(order => {
                    const prevStatus = prevStatusesRef.current[order._id];
                    if (prevStatus && prevStatus !== order.status) {
                        const prevStep = statusToMap[prevStatus] || 0;
                        const newStep = statusToMap[order.status] || 0;
                        if (newStep > prevStep) shouldPlaySound = true;
                    }
                    prevStatusesRef.current[order._id] = order.status;
                });

                if (shouldPlaySound && isMounted) {
                    try {
                        const audio = new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3');
                        audio.volume = 0.5;
                        audio.play().catch(e => console.log('Audio play blocked:', e));
                    } catch (e) { }
                }

                if (isMounted) setOrders(data);
            } catch (err) {
                console.error('Failed to fetch orders', err);
            } finally {
                if (isMounted) setLoading(false);
            }
        };

        if (user) {
            fetchOrders();
            const interval = setInterval(fetchOrders, 5000);
            return () => {
                isMounted = false;
                clearInterval(interval);
            };
        }
    }, [user]);

    if (!user) {
        return <div className="text-center mt-20 text-gray-600">Please login to view profile</div>;
    }

    const filteredOrders = orders.filter(order => statusFilter === 'All' ? true : order.status === statusFilter);

    return (
        <div className="max-w-6xl mx-auto mb-12 flex flex-col md:flex-row gap-8 px-4">
            {/* Left Sidebar: User Details */}
            <div className="md:w-1/3 shrink-0">
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 sticky top-24">
                    {isEditing ? (
                        <form onSubmit={handleUpdateProfile} className="space-y-4">
                            <div className="flex justify-between items-center mb-4">
                                <h3 className="font-bold text-gray-900">Edit Profile</h3>
                                <button type="button" onClick={() => setIsEditing(false)} className="text-gray-400 hover:text-gray-600">
                                    <X size={20} />
                                </button>
                            </div>

                            <div>
                                <label className="block text-xs font-bold text-gray-600 uppercase mb-1">Avatar URL</label>
                                <input type="text" value={formData.avatar} onChange={(e) => setFormData({ ...formData, avatar: e.target.value })} className="w-full border border-gray-300 rounded-lg p-2 text-sm focus:outline-none focus:border-zomato" placeholder="https://..." />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-gray-600 uppercase mb-1">Name</label>
                                <input type="text" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="w-full border border-gray-300 rounded-lg p-2 text-sm focus:outline-none focus:border-zomato" required />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-gray-600 uppercase mb-1">Phone</label>
                                <input type="text" value={formData.phone} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} className="w-full border border-gray-300 rounded-lg p-2 text-sm focus:outline-none focus:border-zomato" />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-gray-600 uppercase mb-1">Address</label>
                                <textarea value={formData.address} onChange={(e) => setFormData({ ...formData, address: e.target.value })} className="w-full border border-gray-300 rounded-lg p-2 text-sm focus:outline-none focus:border-zomato" rows="2"></textarea>
                            </div>

                            <button type="submit" className="w-full bg-zomato text-white font-bold py-2 rounded-lg flex justify-center items-center hover:bg-red-600 transition-colors">
                                <Check size={18} className="mr-2" /> Save Changes
                            </button>
                        </form>
                    ) : (
                        <>
                            <div className="flex justify-between items-start mb-4">
                                {user.avatar ? (
                                    <img src={user.avatar} alt="Avatar" className="w-24 h-24 rounded-full object-cover border-4 border-red-50" />
                                ) : (
                                    <div className="w-24 h-24 bg-red-100 text-zomato rounded-full flex items-center justify-center text-3xl font-bold">
                                        {user.name.charAt(0).toUpperCase()}
                                    </div>
                                )}
                                <button onClick={() => setIsEditing(true)} className="text-gray-400 hover:text-zomato transition-colors p-2 bg-gray-50 rounded-full">
                                    <Edit2 size={16} />
                                </button>
                            </div>

                            <h2 className="text-2xl font-bold text-gray-900 mb-1">{user.name}</h2>
                            <p className="text-gray-500 text-sm mb-6">Foodie Level: Pro Member</p>

                            <div className="space-y-4 pt-4 border-t border-gray-100">
                                <div className="flex items-start space-x-3 text-gray-600">
                                    <Mail size={18} className="mt-0.5 text-gray-400 shrink-0" />
                                    <span className="text-sm break-all">{user.email}</span>
                                </div>
                                <div className="flex items-start space-x-3 text-gray-600">
                                    <Phone size={18} className="mt-0.5 text-gray-400 shrink-0" />
                                    <span className="text-sm">{user.phone || '+91 98765 43210'}</span>
                                </div>
                                <div className="flex items-start space-x-3 text-gray-600">
                                    <MapPin size={18} className="mt-0.5 text-gray-400 shrink-0" />
                                    <span className="text-sm">{user.address || '123 Main Street, Bangalore, Karnataka'}</span>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>

            {/* Right Content: Past Orders */}
            <div className="flex-1">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6">
                    <h2 className="text-xl font-bold text-gray-900 flex items-center mb-4 sm:mb-0">
                        <Clock className="text-zomato mr-2" /> Past Orders
                    </h2>

                    {/* Filter Links */}
                    {!loading && orders.length > 0 && (
                        <div className="flex bg-gray-100 p-1 rounded-lg">
                            {['All', 'Preparing', 'Out for Delivery', 'Delivered'].map(status => (
                                <button
                                    key={status}
                                    onClick={() => setStatusFilter(status)}
                                    className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${statusFilter === status ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-800'}`}
                                >
                                    {status}
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {loading ? (
                    <div className="flex justify-center p-8"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-zomato"></div></div>
                ) : orders.length === 0 ? (
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 text-center flex flex-col items-center justify-center animate-slide-up">
                        <div className="w-32 h-32 bg-red-50 rounded-full flex items-center justify-center mb-6">
                            <Clock size={48} className="text-zomato" />
                        </div>
                        <h3 className="text-xl font-bold text-gray-900 mb-2">No Past Orders</h3>
                        <p className="text-gray-500 mb-6">You haven't placed any orders yet. Let's fix that!</p>
                        <Link to="/" className="bg-zomato text-white px-6 py-3 rounded-xl font-bold hover:bg-red-600 transition-colors">
                            Explore Restaurants
                        </Link>
                    </div>
                ) : filteredOrders.length === 0 ? (
                    <div className="py-12 text-center text-gray-500">No orders match the selected filter.</div>
                ) : (
                    <div className="space-y-5">
                        {filteredOrders.map(order => (
                            <div key={order._id} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 hover:border-red-200 transition-all group overflow-hidden">

                                {/* Order Header (Restaurant Info) */}
                                <div className="flex justify-between items-start mb-4 pb-4 border-b border-gray-50">
                                    <Link to={`/restaurant/${order.restaurant_id}`} className="flex items-center space-x-3 cursor-pointer group/rest hover:opacity-80 transition-opacity">
                                        <div className="w-12 h-12 bg-gray-100 rounded-xl overflow-hidden shadow-sm shrink-0">
                                            {order.restaurant?.image_url && (
                                                <img src={order.restaurant.image_url} alt={order.restaurant.name} className="w-full h-full object-cover" />
                                            )}
                                        </div>
                                        <div>
                                            <h4 className="font-bold text-gray-900 text-lg group-hover/rest:text-zomato flex items-center">
                                                {order.restaurant?.name || `Restaurant ID: ${order.restaurant_id}`}
                                                <ChevronRight size={16} className="ml-0.5 text-gray-400 group-hover/rest:translate-x-1 transition-transform" />
                                            </h4>
                                            <p className="text-xs text-gray-500 mt-0.5">{order.restaurant?.city}</p>
                                        </div>
                                    </Link>

                                    <div className="text-right flex flex-col items-end">
                                        <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold mb-1 ${order.status === 'Delivered' ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'
                                            }`}>
                                            {order.status}
                                        </span>
                                        <p className="text-xs text-gray-400">Order #{order._id.substring(order._id.length - 8).toUpperCase()}</p>
                                    </div>
                                </div>

                                {/* Order Items Thumbnail Display */}
                                <div className="mb-4">
                                    <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Items Ordered</p>
                                    {order.populatedItems && order.populatedItems.length > 0 ? (
                                        <div className="flex flex-wrap gap-2">
                                            {order.populatedItems.map((item, idx) => (
                                                <Link
                                                    to={`/restaurant/${order.restaurant_id}`}
                                                    key={`${item.item_id}-${idx}`}
                                                    className="flex items-center bg-gray-50 border border-gray-100 rounded-lg p-1.5 pr-3 hover:bg-gray-100 hover:border-gray-300 transition-colors cursor-pointer"
                                                    title={`Go to restaurant to order ${item.name} again`}
                                                >
                                                    <div className="w-8 h-8 rounded-md bg-gray-200 overflow-hidden mr-2 shrink-0">
                                                        <img src={item.image_url || 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=100&q=80'} alt={item.name} className="w-full h-full object-cover" />
                                                    </div>
                                                    <div className="flex flex-col">
                                                        <span className="text-sm font-medium text-gray-800 limit-1-line" style={{ maxWidth: '120px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.name}</span>
                                                        <span className="text-xs text-gray-500">Qty: {item.quantity}</span>
                                                    </div>
                                                </Link>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="text-sm text-gray-500 italic">Item details unavailable (ID: {order.items.join(', ')})</div>
                                    )}
                                </div>

                                {/* Order Footer */}
                                <div className="flex justify-between items-center border-t border-gray-50 pt-4 bg-gray-50/50 -mx-5 -mb-5 px-5 pb-5">
                                    <div className="text-sm text-gray-500">
                                        {new Date(order.createdAt).toLocaleDateString()} at {new Date(order.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </div>
                                    <div className="flex items-center space-x-4">
                                        <div className="font-bold text-gray-900">
                                            ₹{order.totalAmount.toFixed(2)}
                                        </div>
                                        <Link
                                            to={`/order/${order._id}`}
                                            className="text-sm font-bold text-zomato bg-red-50 hover:bg-red-100 px-4 py-1.5 rounded-lg transition-colors border border-red-100"
                                        >
                                            Track Order
                                        </Link>
                                    </div>
                                </div>

                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default Profile;
