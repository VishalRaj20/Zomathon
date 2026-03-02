import React, { useState, useEffect, useContext, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { CheckCircle2, Clock, MapPin, ChefHat, Bike, ArrowLeft, Phone, Star } from 'lucide-react';
import api from '../api/axios';
import { AuthContext } from '../context/AuthContext';

const OrderTracking = () => {
    const { id } = useParams();
    const [order, setOrder] = useState(null);
    const [loading, setLoading] = useState(true);
    const prevStatusRef = useRef(null);

    // Mapping string status to progress integers
    const statusToMap = {
        'Preparing': 1,
        'Out for Delivery': 2,
        'Delivered': 3
    };

    const [estimatedDelivery, setEstimatedDelivery] = useState('15-20 mins');

    useEffect(() => {
        const fetchOrder = async () => {
            try {
                const { data } = await api.get(`/orders/${id}`);
                setOrder(data);
                prevStatusRef.current = data.status;
            } catch (err) {
                console.error('Error fetching order:', err);
            } finally {
                setLoading(false);
            }
        };
        fetchOrder();

        // Simulate Zomato real-time tracking by polling lightweight status every 5s
        const interval = setInterval(async () => {
            try {
                const { data } = await api.get(`/orders/${id}/status`);

                if (prevStatusRef.current && prevStatusRef.current !== data.status) {
                    const prevStep = statusToMap[prevStatusRef.current] || 0;
                    const newStep = statusToMap[data.status] || 0;

                    if (newStep > prevStep) {
                        try {
                            // Play a pleasant notification chime
                            const audio = new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3');
                            audio.volume = 0.5;
                            audio.play().catch(e => console.log('Audio play blocked by browser:', e));
                        } catch (e) {
                            console.error('Audio error', e);
                        }
                    }
                    prevStatusRef.current = data.status;
                }

                setOrder(prev => prev ? { ...prev, status: data.status } : null);
                if (data.estimatedDelivery) {
                    setEstimatedDelivery(data.estimatedDelivery);
                }
            } catch (err) {
                console.error('Error fetching tracking status:', err);
            }
        }, 5000);

        return () => clearInterval(interval);
    }, [id]);

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-zomato"></div>
            </div>
        );
    }

    if (!order) {
        return (
            <div className="text-center mt-20 text-gray-600">
                <h2 className="text-2xl font-bold mb-4">Order Not Found</h2>
                <Link to="/" className="text-zomato hover:underline">Return Home</Link>
            </div>
        );
    }

    const currentStep = statusToMap[order.status] || 1;

    return (
        <div className="max-w-3xl mx-auto mb-12">
            <Link to="/" className="inline-flex items-center text-gray-500 hover:text-zomato mb-6 transition-colors font-medium">
                <ArrowLeft size={18} className="mr-1" /> Back to Home
            </Link>

            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden animate-slide-up">
                {/* Header Map Graphic */}
                <div className="h-48 bg-slate-100 relative w-full overflow-hidden">
                    <img
                        src="https://images.unsplash.com/photo-1524661135-423995f22d0b?w=800&q=80"
                        alt="Map background"
                        className="w-full h-full object-cover opacity-60 mix-blend-multiply grayscale"
                    />
                    <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                        <div className="bg-white/90 backdrop-blur-sm px-6 py-4 rounded-2xl shadow-lg border border-white/50 animate-pulse-slow">
                            <h2 className="text-xl font-bold text-gray-900 text-center">
                                {order.status === 'Delivered' ? 'Successfully Delivered' : `Arriving in ${estimatedDelivery}`}
                            </h2>
                            <p className="text-sm text-gray-500 text-center flex items-center justify-center mt-1">
                                <MapPin size={14} className="mr-1 text-zomato" /> Delivery to Home
                            </p>
                        </div>
                    </div>
                </div>

                <div className="p-8">
                    <h3 className="text-2xl font-black text-gray-900 mb-8 border-b border-gray-100 pb-4">
                        Order #{order._id.substring(order._id.length - 6).toUpperCase()}
                    </h3>

                    {/* Stepper Tracking UI */}
                    <div className="relative mb-12">
                        <div className="absolute top-1/2 left-0 w-full h-1 bg-gray-100 -translate-y-1/2 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-green-500 transition-all duration-1000 ease-in-out"
                                style={{ width: `${(currentStep - 1) * 50}%` }}
                            ></div>
                        </div>

                        <div className="relative z-10 flex justify-between">
                            {/* Step 1 */}
                            <div className="flex flex-col items-center group">
                                <div className={`w-12 h-12 rounded-full flex items-center justify-center border-4 transition-colors ${currentStep >= 1 ? 'bg-white border-green-500 text-green-500' : 'bg-white border-gray-200 text-gray-300'}`}>
                                    <ChefHat size={20} className={currentStep === 1 ? 'animate-bounce' : ''} />
                                </div>
                                <p className={`mt-3 font-bold text-sm ${currentStep >= 1 ? 'text-gray-900' : 'text-gray-400'}`}>Preparing</p>
                            </div>

                            {/* Step 2 */}
                            <div className="flex flex-col items-center group">
                                <div className={`w-12 h-12 rounded-full flex items-center justify-center border-4 transition-colors ${currentStep >= 2 ? 'bg-white border-green-500 text-green-500' : 'bg-white border-gray-200 text-gray-300'}`}>
                                    <Bike size={20} className={currentStep === 2 ? 'animate-bounce' : ''} />
                                </div>
                                <p className={`mt-3 font-bold text-sm ${currentStep >= 2 ? 'text-gray-900' : 'text-gray-400'}`}>Out for delivery</p>
                            </div>

                            {/* Step 3 */}
                            <div className="flex flex-col items-center group">
                                <div className={`w-12 h-12 rounded-full flex items-center justify-center border-4 transition-colors ${currentStep >= 3 ? 'bg-white border-green-500 text-green-500' : 'bg-white border-gray-200 text-gray-300'}`}>
                                    <CheckCircle2 size={24} />
                                </div>
                                <p className={`mt-3 font-bold text-sm ${currentStep >= 3 ? 'text-gray-900' : 'text-gray-400'}`}>Delivered</p>
                            </div>
                        </div>
                    </div>

                    {/* Delivery Partner Details */}
                    {currentStep >= 2 && (
                        <div className="bg-white border border-gray-100 rounded-xl p-4 flex items-center shadow-sm mb-6 mt-4 animate-slide-up" style={{ animationDelay: '200ms' }}>
                            <img
                                src="https://images.unsplash.com/photo-1599566150163-29194dcaad36?w=100&h=100&fit=crop"
                                alt="Rider"
                                className="w-16 h-16 rounded-full object-cover mr-4"
                            />
                            <div className="flex-1">
                                <h4 className="font-bold text-gray-900 text-lg">Ramesh Kumar</h4>
                                <div className="flex items-center text-sm text-gray-500 space-x-2">
                                    <span className="flex items-center text-green-600 font-bold bg-green-50 px-1.5 py-0.5 rounded">
                                        4.8 <Star size={12} className="ml-0.5" fill="currentColor" />
                                    </span>
                                    <span>•</span>
                                    <span>2,143 deliveries</span>
                                </div>
                            </div>
                            <a href="tel:8888888888" className="bg-green-100 text-green-700 p-3 rounded-full hover:bg-green-200 transition-colors flex items-center justify-center" title="Call Rider">
                                <Phone size={20} />
                            </a>
                        </div>
                    )}

                    {/* Restaurant Contact Details */}
                    <div className="bg-white border border-gray-100 rounded-xl p-4 flex items-center shadow-sm mb-6 mt-4">
                        <div className="w-16 h-16 bg-red-50 text-zomato rounded-2xl flex items-center justify-center mr-4">
                            <ChefHat size={32} />
                        </div>
                        <div className="flex-1">
                            <h4 className="font-bold text-gray-900 text-lg">Restaurant Need Help?</h4>
                            <p className="text-sm text-gray-500">Contact the outlet directly</p>
                            <p className="text-sm font-medium text-gray-700 mt-1">+91 91234 56789</p>
                        </div>
                        <a href="tel:9123456789" className="bg-gray-100 text-gray-700 p-3 rounded-full hover:bg-gray-200 transition-colors flex items-center justify-center" title="Call Restaurant">
                            <Phone size={20} />
                        </a>
                    </div>

                    <div className="bg-gray-50 rounded-xl p-5 border border-gray-100">
                        <h4 className="font-bold text-gray-800 mb-3 flex items-center"><Clock size={18} className="mr-2 text-gray-400" /> Order Summary</h4>
                        <div className="space-y-2 text-sm text-gray-600 mb-4 pb-4 border-b border-gray-200">
                            <p>Restaurant ID: <span className="font-medium text-gray-900">{order.restaurant_id}</span></p>
                            <p>Items in Order: <span className="font-medium text-gray-900">{order.items.length} items</span></p>
                            <p>Placed at: <span className="font-medium text-gray-900">{new Date(order.createdAt).toLocaleTimeString()}</span></p>
                        </div>
                        <div className="flex justify-between items-center text-lg font-bold text-gray-900">
                            <span>Total Amount Paid</span>
                            <span>₹{order.totalAmount.toFixed(2)}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default OrderTracking;
