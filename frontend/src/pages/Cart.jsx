import React, { useContext, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShoppingBag, ChevronRight, Sparkles, CreditCard, Banknote, Smartphone, CheckCircle2, X } from 'lucide-react';
import { CartContext } from '../context/CartContext';
import { AuthContext } from '../context/AuthContext';
import { LocationContext } from '../context/LocationContext';
import CartItem from '../components/CartItem';
import RecommendationCard from '../components/RecommendationCard';
import api from '../api/axios';

const Cart = () => {
    const { cart, clearCart } = useContext(CartContext);
    const { user } = useContext(AuthContext);
    const { location } = useContext(LocationContext);
    const [cartDetails, setCartDetails] = useState([]);
    const [recommendations, setRecommendations] = useState([]);
    const [loading, setLoading] = useState(false);
    const [total, setTotal] = useState(0);

    // Payment State
    const [showPaymentModal, setShowPaymentModal] = useState(false);
    const [paymentStep, setPaymentStep] = useState('select'); // select -> details -> processing -> success
    const [paymentMethod, setPaymentMethod] = useState('card');

    // Dummy Form State
    const [dummyUpi, setDummyUpi] = useState('');
    const [dummyCard, setDummyCard] = useState({ number: '', expiry: '', cvv: '', name: '' });

    useEffect(() => {
        const fetchRecommendationsAndCart = async () => {
            setLoading(true);
            try {
                // Fetch recommendations whether cart is empty or not!
                const res = await api.post('/recommend', {
                    top_k: 6,
                    cart_items: cart,
                    timestamp: new Date().toISOString(),
                    city: location
                });

                console.log("Recommend API Response:", res.data);

                const fetchedCart = res.data.cart_items || [];
                const fetchedRecs = res.data.recommendations || [];

                if (cart.length > 0 && fetchedCart.length === 0) {
                    clearCart();
                    setCartDetails([]);
                    setTotal(0);
                } else if (cart.length > 0) {
                    setCartDetails(fetchedCart);
                    const sum = fetchedCart.reduce((acc, item) => acc + item.price, 0);
                    setTotal(sum);
                } else {
                    setCartDetails([]);
                    setTotal(0);
                }

                setRecommendations(fetchedRecs);
            } catch (err) {
                console.error("Failed to fetch ML data:", err);
            } finally {
                setLoading(false);
            }
        };

        fetchRecommendationsAndCart();
    }, [cart]);

    const navigate = useNavigate();

    const smallOrderFee = total > 0 && total < 100 ? 25 : 0;
    const finalTotal = total > 0 ? total + 5 + smallOrderFee + (total * 0.05) : 0;

    const handleContinueToDetails = () => {
        if (paymentMethod === 'cod') {
            handleProcessPayment();
        } else {
            setPaymentStep('details');
        }
    };

    const handleProcessPayment = () => {
        setPaymentStep('processing');
        setTimeout(async () => {
            setPaymentStep('success');
            setTimeout(() => {
                executeOrderPlacement();
            }, 500);
        }, 500);
    };

    const executeOrderPlacement = async () => {
        try {
            const restaurant_id = cartDetails.length > 0 ? cartDetails[0].restaurant_id : 48;

            const res = await api.post('/orders', {
                restaurant_id: restaurant_id,
                items: cart,
                totalAmount: finalTotal
            });
            await clearCart();
            setShowPaymentModal(false);
            setPaymentStep('select');
            navigate(`/order/${res.data._id}`);
        } catch (err) {
            console.error('Failed to place order', err);
            alert('Failed to place order. Please try again.');
            setShowPaymentModal(false);
            setPaymentStep('select');
        }
    };

    if (cart.length === 0) {
        return (
            <div className="max-w-6xl mx-auto flex flex-col items-center justify-center min-h-[60vh] py-8">
                <div className="text-center mb-16 animate-fade-in flex flex-col items-center">
                    <div className="w-24 h-24 bg-red-50 rounded-full flex items-center justify-center mb-6">
                        <ShoppingBag size={48} className="text-zomato" />
                    </div>
                    <h2 className="text-3xl font-black text-gray-900 mb-3">Your cart is empty</h2>
                    <p className="text-gray-500 max-w-sm text-lg">Good food is always cooking! Go ahead and explore top restaurants.</p>
                </div>

                {/* Global Context Recommendations */}
                {recommendations.length > 0 && (
                    <div className="w-full px-4 mt-2 animate-slide-up">
                        <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center justify-center gap-2">
                            <Sparkles className="text-yellow-500" size={24} />
                            Trending Near You Right Now
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
                            {recommendations.slice(0, 6).map(rec => (
                                <RecommendationCard key={rec.item_id} item={rec} />
                            ))}
                        </div>
                    </div>
                )}
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto flex flex-col lg:flex-row gap-8 relative">
            {/* Left side: Cart Items */}
            <div className="flex-1 w-full">
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 md:p-6 mb-6 overflow-hidden">
                    <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                        <ShoppingBag className="text-zomato" /> Secure Checkout
                    </h2>

                    <div className="space-y-1 mb-6">
                        {Array.from(new Set(cartDetails.map(item => item.item_id)))
                            .map(id => cartDetails.find(item => item.item_id === id))
                            .map(item => (
                                <CartItem key={item.item_id} item={item} />
                            ))}
                    </div>

                    <div className="border-t border-gray-100 pt-4 cursor-pointer text-zomato font-medium hover:text-red-600 transition-colors inline-block" onClick={clearCart}>
                        Clear Cart
                    </div>
                </div>

                {/* The Magic ML Section */}
                {recommendations.length > 0 && (
                    <div className="mt-8">
                        <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                            <Sparkles className="text-yellow-500" size={20} />
                            Frequently Bought Together
                        </h3>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            {recommendations.map(rec => (
                                <RecommendationCard key={rec.item_id} item={rec} />
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Right side: Bill Details */}
            <div className="w-full lg:w-96 shrink-0">
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 md:p-6 sticky top-24 mx-auto w-full">
                    <h3 className="text-lg font-bold text-gray-900 mb-4">Bill Details</h3>

                    <div className="space-y-3 text-gray-600 mb-6 pb-6 border-b border-gray-100 text-sm">
                        <div className="flex justify-between">
                            <span>Item Total</span>
                            <span className="font-medium text-gray-800">₹{total.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between text-gray-500">
                            <span className="flex items-center">Delivery Partner Fee <span className="ml-1 text-xs bg-blue-100 text-blue-700 px-1 rounded">PRO</span></span>
                            <span><del className="mr-2">₹45</del> <span className="text-green-600">FREE</span></span>
                        </div>
                        <div className="flex justify-between">
                            <span>Platform Fee</span>
                            <span>₹5.00</span>
                        </div>
                        {smallOrderFee > 0 && (
                            <div className="flex justify-between text-yellow-600">
                                <span>Small Order Fee <span className="text-xs text-gray-400 block">Orders below ₹100</span></span>
                                <span>₹{smallOrderFee.toFixed(2)}</span>
                            </div>
                        )}
                        <div className="flex justify-between">
                            <span>GST and Restaurant Charges</span>
                            <span>₹{(total * 0.05).toFixed(2)}</span>
                        </div>
                    </div>

                    <div className="flex justify-between items-center mb-6">
                        <span className="font-bold text-gray-900 text-lg">TO PAY</span>
                        <span className="font-bold text-gray-900 text-xl">₹{finalTotal.toFixed(2)}</span>
                    </div>

                    <button
                        onClick={() => setShowPaymentModal(true)}
                        disabled={loading}
                        className="w-full bg-zomato text-white font-bold py-4 rounded-xl shadow-lg shadow-red-200 hover:bg-red-600 hover:shadow-xl hover:-translate-y-0.5 transition-all flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <span>{loading ? 'Preparing...' : 'Select Payment'}</span>
                        <ChevronRight size={20} />
                    </button>
                </div>
            </div>

            {/* Highly Realistic Dummy Payment Gateway */}
            {showPaymentModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4 animate-fade-in">
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden relative flex flex-col" style={{ height: '600px', maxHeight: '90vh' }}>

                        {/* Gateway Header */}
                        <div className="bg-[#0b1215] text-white px-6 py-5 flex justify-between items-center shrink-0">
                            <div className="flex items-center space-x-3">
                                <div className="w-8 h-8 bg-white rounded flex items-center justify-center font-bold text-[#0b1215]">
                                    z
                                </div>
                                <div>
                                    <h3 className="font-bold text-lg leading-tight">Zomathon Pay</h3>
                                    <p className="text-xs text-gray-400 opacity-80">Test Environment</p>
                                </div>
                            </div>
                            <div className="text-right">
                                <div className="font-bold text-xl leading-tight">₹{finalTotal.toFixed(2)}</div>
                                <button onClick={() => { setShowPaymentModal(false); setPaymentStep('select'); }} className="text-xs text-gray-400 hover:text-white mt-1 opacity-80 hover:opacity-100 flex items-center justify-end">
                                    <X size={12} className="mr-1" /> CANCEL
                                </button>
                            </div>
                        </div>

                        {/* Gateway Body */}
                        <div className="flex-1 overflow-y-auto bg-gray-50 flex flex-col">

                            {/* Step 1: Select Method */}
                            {paymentStep === 'select' && (
                                <div className="flex-1 animate-slide-up">
                                    <div className="p-4 flex items-center justify-between text-sm font-medium text-gray-500 bg-white border-b border-gray-100">
                                        <div className="flex items-center">
                                            <div className="bg-gray-100 p-1.5 rounded mr-3 text-gray-600"><Smartphone size={16} /></div>
                                            <span>Guest User <br /><span className="text-xs text-gray-400">9876543210</span></span>
                                        </div>
                                    </div>
                                    <div className="p-6">
                                        <p className="text-xs font-bold text-gray-400 mb-4 uppercase tracking-wider">Cards, UPI & More</p>
                                        <div className="bg-white border text-left border-gray-200 rounded-xl overflow-hidden divide-y divide-gray-100 shadow-sm">

                                            {/* UPI */}
                                            <button onClick={() => setPaymentMethod('upi')} className={`w-full flex items-center p-4 transition-colors ${paymentMethod === 'upi' ? 'bg-[#f4f8fb]' : 'hover:bg-gray-50'}`}>
                                                <input type="radio" readOnly checked={paymentMethod === 'upi'} className="w-4 h-4 text-blue-600 focus:ring-blue-600 border-gray-300 mr-4 shrink-0" />
                                                <div className="flex items-center">
                                                    <div className="w-8 h-8 rounded bg-blue-50 flex items-center justify-center mr-3 text-blue-600 shrink-0"><Smartphone size={16} /></div>
                                                    <div className="text-left"><span className="block font-bold text-gray-900 text-sm">UPI / QR</span><span className="text-xs text-gray-500">Google Pay, PhonePe, Paytm</span></div>
                                                </div>
                                            </button>

                                            {/* Card */}
                                            <button onClick={() => setPaymentMethod('card')} className={`w-full flex items-center p-4 transition-colors ${paymentMethod === 'card' ? 'bg-[#f4f8fb]' : 'hover:bg-gray-50'}`}>
                                                <input type="radio" readOnly checked={paymentMethod === 'card'} className="w-4 h-4 text-blue-600 focus:ring-blue-600 border-gray-300 mr-4 shrink-0" />
                                                <div className="flex items-center">
                                                    <div className="w-8 h-8 rounded bg-gray-100 flex items-center justify-center mr-3 text-gray-600 shrink-0"><CreditCard size={16} /></div>
                                                    <div className="text-left"><span className="block font-bold text-gray-900 text-sm">Card</span><span className="text-xs text-gray-500">Visa, MasterCard, RuPay</span></div>
                                                </div>
                                            </button>

                                            {/* COD */}
                                            <button onClick={() => setPaymentMethod('cod')} className={`w-full flex items-center p-4 transition-colors ${paymentMethod === 'cod' ? 'bg-[#f4f8fb]' : 'hover:bg-gray-50'}`}>
                                                <input type="radio" readOnly checked={paymentMethod === 'cod'} className="w-4 h-4 text-blue-600 focus:ring-blue-600 border-gray-300 mr-4 shrink-0" />
                                                <div className="flex items-center">
                                                    <div className="w-8 h-8 rounded bg-green-50 flex items-center justify-center mr-3 text-green-600 shrink-0"><Banknote size={16} /></div>
                                                    <div className="text-left"><span className="block font-bold text-gray-900 text-sm">Cash on Delivery</span><span className="text-xs text-gray-500">Pay directly to rider</span></div>
                                                </div>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Step 2: Input Details */}
                            {paymentStep === 'details' && (
                                <div className="flex-1 bg-white p-6 animate-slide-up flex flex-col">
                                    <button onClick={() => setPaymentStep('select')} className="text-sm text-blue-600 font-medium mb-6 flex items-center hover:underline w-fit">
                                        <span>← Back to Methods</span>
                                    </button>

                                    {paymentMethod === 'upi' ? (
                                        <div className="flex-1">
                                            <div className="flex items-center space-x-3 mb-6">
                                                <div className="w-10 h-10 rounded bg-blue-50 flex items-center justify-center text-blue-600"><Smartphone size={20} /></div>
                                                <h3 className="font-bold text-gray-900 text-lg">Pay via UPI</h3>
                                            </div>
                                            <label className="block text-sm font-medium text-gray-700 mb-2">Virtual Payment Address (UPI ID)</label>
                                            <input
                                                type="text"
                                                placeholder="e.g. 9876543210@ybl"
                                                value={dummyUpi}
                                                onChange={(e) => setDummyUpi(e.target.value)}
                                                className="w-full border border-gray-300 rounded-lg px-4 py-3 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all font-mono mb-4 text-base"
                                            />
                                            <p className="text-xs text-gray-500 leading-relaxed bg-blue-50 p-3 rounded-lg border border-blue-100">
                                                A payment request will be sent to your UPI app. Please approve it within 5 minutes.
                                            </p>
                                        </div>
                                    ) : (
                                        <div className="flex-1">
                                            <div className="flex items-center space-x-3 mb-6">
                                                <div className="w-10 h-10 rounded bg-gray-100 flex items-center justify-center text-gray-600"><CreditCard size={20} /></div>
                                                <h3 className="font-bold text-gray-900 text-lg">Enter Card Details</h3>
                                            </div>
                                            <div className="space-y-4">
                                                <div>
                                                    <label className="block text-xs font-medium text-gray-700 mb-1">Card Number</label>
                                                    <input type="text" placeholder="XXXX XXXX XXXX XXXX" maxLength="19" value={dummyCard.number} onChange={(e) => setDummyCard({ ...dummyCard, number: e.target.value })} className="w-full border border-gray-300 rounded-lg px-4 py-2.5 outline-none focus:border-blue-500 font-mono tracking-widest text-gray-800" />
                                                </div>
                                                <div className="flex space-x-4">
                                                    <div className="flex-1">
                                                        <label className="block text-xs font-medium text-gray-700 mb-1">Expiry (MM/YY)</label>
                                                        <input type="text" placeholder="MM/YY" maxLength="5" value={dummyCard.expiry} onChange={(e) => setDummyCard({ ...dummyCard, expiry: e.target.value })} className="w-full border border-gray-300 rounded-lg px-4 py-2.5 outline-none focus:border-blue-500 font-mono text-gray-800" />
                                                    </div>
                                                    <div className="flex-1">
                                                        <label className="block text-xs font-medium text-gray-700 mb-1">CVV</label>
                                                        <input type="password" placeholder="•••" maxLength="4" value={dummyCard.cvv} onChange={(e) => setDummyCard({ ...dummyCard, cvv: e.target.value })} className="w-full border border-gray-300 rounded-lg px-4 py-2.5 outline-none focus:border-blue-500 font-mono text-gray-800 tracking-widest" />
                                                    </div>
                                                </div>
                                                <div>
                                                    <label className="block text-xs font-medium text-gray-700 mb-1">Name on Card</label>
                                                    <input type="text" placeholder="John Doe" value={dummyCard.name} onChange={(e) => setDummyCard({ ...dummyCard, name: e.target.value })} className="w-full border border-gray-300 rounded-lg px-4 py-2.5 outline-none focus:border-blue-500 text-gray-800" />
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Step 3 & 4: Processing / Success */}
                            {(paymentStep === 'processing' || paymentStep === 'success') && (
                                <div className="flex-1 flex flex-col items-center justify-center p-8 bg-white text-center animate-fade-in">
                                    {paymentStep === 'success' ? (
                                        <>
                                            <div className="w-24 h-24 bg-green-50 rounded-full flex items-center justify-center mb-6 ring-8 ring-green-100 animate-pulse">
                                                <CheckCircle2 size={48} className="text-green-500" />
                                            </div>
                                            <h2 className="text-2xl font-bold text-gray-900 mb-2">Payment Successful</h2>
                                            <p className="text-gray-500">Redirecting to Zomathon...</p>
                                        </>
                                    ) : (
                                        <>
                                            <div className="relative w-24 h-24 flex items-center justify-center mb-6">
                                                <div className="absolute inset-0 border-4 border-gray-100 rounded-full"></div>
                                                <div className="absolute inset-0 border-4 border-t-blue-500 border-r-blue-500 rounded-full animate-spin"></div>
                                                <div className="w-10 h-10 bg-blue-50 rounded-full flex items-center justify-center font-bold text-blue-500 text-xl">z</div>
                                            </div>
                                            <h2 className="text-xl font-bold text-gray-900 mb-2">Awaiting Confirmation</h2>
                                            <p className="text-gray-500 text-sm">Do not refresh your browser or hit back.</p>
                                        </>
                                    )}
                                </div>
                            )}

                        </div>

                        {/* Gateway Footer button */}
                        {(paymentStep === 'select' || paymentStep === 'details') && (
                            <div className="p-4 bg-white border-t border-gray-100 shrink-0">
                                <button
                                    onClick={paymentStep === 'select' ? handleContinueToDetails : handleProcessPayment}
                                    className="w-full bg-[#0b1215] text-white font-bold py-4 rounded-xl shadow-lg shadow-gray-300 hover:bg-black hover:-translate-y-0.5 transition-all text-lg flex items-center justify-center relative"
                                >
                                    PAY ₹{finalTotal.toFixed(2)}
                                    {(paymentMethod === 'upi' && paymentStep === 'select') && <span className="absolute right-6 opacity-70 border border-white/30 text-[10px] px-2 py-0.5 rounded tracking-widest uppercase">FAST</span>}
                                </button>
                                <div className="text-center mt-3 flex items-center justify-center text-xs text-gray-400">
                                    <Sparkles size={12} className="mr-1 text-blue-500" /> Secured by AES-256 Encryption
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default Cart;
