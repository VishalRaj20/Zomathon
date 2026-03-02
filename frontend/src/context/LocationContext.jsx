import React, { createContext, useState } from 'react';

export const LocationContext = createContext();

export const LocationProvider = ({ children }) => {
    const [location, setLocationState] = useState(() => {
        return localStorage.getItem('userLocation') || 'Bangalore';
    });

    const setLocation = (newCity) => {
        localStorage.setItem('userLocation', newCity);
        setLocationState(newCity);
    };

    return (
        <LocationContext.Provider value={{ location, setLocation }}>
            {children}
        </LocationContext.Provider>
    );
};
