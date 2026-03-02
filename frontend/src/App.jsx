import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { CartProvider } from './context/CartContext';
import { LocationProvider } from './context/LocationContext';

import Navbar from './components/Navbar';
import Footer from './components/Footer';
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import Restaurant from './pages/Restaurant';
import Cart from './pages/Cart';
import OrderTracking from './pages/OrderTracking';
import Profile from './pages/Profile';
import PrivateRoute from './routes/PrivateRoute';

function App() {
    return (
        <Router>
            <AuthProvider>
                <LocationProvider>
                    <CartProvider>
                        <div className="flex flex-col min-h-screen">
                            <Navbar />
                            <main className="flex-grow container mx-auto px-4 py-8">
                                <Routes>
                                    <Route path="/" element={<Home />} />
                                    <Route path="/login" element={<Login />} />
                                    <Route path="/register" element={<Register />} />
                                    <Route path="/restaurant/:id" element={<Restaurant />} />
                                    <Route
                                        path="/cart"
                                        element={
                                            <PrivateRoute>
                                                <Cart />
                                            </PrivateRoute>
                                        }
                                    />
                                    <Route
                                        path="/order/:id"
                                        element={
                                            <PrivateRoute>
                                                <OrderTracking />
                                            </PrivateRoute>
                                        }
                                    />
                                    <Route
                                        path="/profile"
                                        element={
                                            <PrivateRoute>
                                                <Profile />
                                            </PrivateRoute>
                                        }
                                    />
                                </Routes>
                            </main>
                            <Footer />
                        </div>
                    </CartProvider>
                </LocationProvider>
            </AuthProvider>
        </Router>
    );
}

export default App;
