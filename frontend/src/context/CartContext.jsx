import React, { createContext, useState, useEffect, useContext, useRef } from 'react';
import api from '../api/axios';
import { AuthContext } from './AuthContext';
import { LocationContext } from './LocationContext';

export const CartContext = createContext();

export const CartProvider = ({ children }) => {
    const [cart, setCart] = useState([]);
    const { user } = useContext(AuthContext);
    const { location } = useContext(LocationContext);
    const prevLocationRef = useRef(location);

    useEffect(() => {
        if (user) {
            fetchCart();
        } else {
            setCart([]);
        }
    }, [user]);

    // Clear cart when city changes (not on initial mount)
    useEffect(() => {
        if (prevLocationRef.current !== location) {
            prevLocationRef.current = location;
            if (user) {
                clearCart();
            } else {
                setCart([]);
            }
        }
    }, [location]);

    const fetchCart = async () => {
        try {
            const { data } = await api.get('/cart');
            setCart(data);
        } catch (error) {
            console.error('Failed to fetch cart:', error.message);
        }
    };

    const addToCart = async (item_id) => {
        if (!user) return alert('Please login to add to cart!');
        try {
            const { data } = await api.post('/cart/add', { item_id });
            setCart(data);
        } catch (error) {
            console.error(error);
        }
    };

    const removeFromCart = async (item_id) => {
        try {
            const { data } = await api.post('/cart/remove', { item_id });
            setCart(data);
        } catch (error) {
            console.error(error);
        }
    };

    const decrementFromCart = async (item_id) => {
        try {
            const { data } = await api.post('/cart/decrement', { item_id });
            setCart(data);
        } catch (error) {
            console.error(error);
        }
    };

    const clearCart = async () => {
        try {
            const { data } = await api.post('/cart/clear');
            setCart(data);
        } catch (error) {
            console.error(error);
        }
    };

    return (
        <CartContext.Provider value={{ cart, addToCart, removeFromCart, decrementFromCart, clearCart }}>
            {children}
        </CartContext.Provider>
    );
};
