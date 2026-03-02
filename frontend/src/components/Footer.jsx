import React from 'react';
import { Facebook, Twitter, Instagram, Linkedin, Mail, Phone, MapPin } from 'lucide-react';

const Footer = () => {
    return (
        <footer className="bg-gray-900 text-gray-300 py-12 mt-16">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
                    {/* Brand Section */}
                    <div>
                        <h2 className="text-3xl font-extrabold text-white tracking-tight mb-4">
                            zoma<span className="text-zomato">thon</span>
                        </h2>
                        <p className="text-gray-400 text-sm mb-6">
                            Delivering the best food & drinks right to your doorstep, instantly and securely.
                        </p>
                        <div className="flex space-x-4">
                            <a href="#" className="text-gray-400 hover:text-white transition-colors"><Facebook size={20} /></a>
                            <a href="#" className="text-gray-400 hover:text-white transition-colors"><Twitter size={20} /></a>
                            <a href="#" className="text-gray-400 hover:text-white transition-colors"><Instagram size={20} /></a>
                            <a href="#" className="text-gray-400 hover:text-white transition-colors"><Linkedin size={20} /></a>
                        </div>
                    </div>

                    {/* Quick Links */}
                    <div>
                        <h3 className="text-white font-bold text-lg mb-4">Quick Links</h3>
                        <ul className="space-y-2 text-sm text-gray-400">
                            <li><a href="#" className="hover:text-white transition-colors">About Zomathon</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Feeding India</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Contact Us</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Report Fraud</a></li>
                        </ul>
                    </div>

                    {/* For Restaurants */}
                    <div>
                        <h3 className="text-white font-bold text-lg mb-4">For Restaurants</h3>
                        <ul className="space-y-2 text-sm text-gray-400">
                            <li><a href="#" className="hover:text-white transition-colors">Partner With Us</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Apps For You</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Restaurant Guidelines</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Business App</a></li>
                        </ul>
                    </div>

                    {/* Contact Info */}
                    <div>
                        <h3 className="text-white font-bold text-lg mb-4">Contact Us</h3>
                        <ul className="space-y-3 text-sm text-gray-400">
                            <li className="flex items-start space-x-3">
                                <MapPin size={16} className="mt-1 shrink-0 text-zomato" />
                                <span>123 Food Street, Tech Park, Bangalore 560001</span>
                            </li>
                            <li className="flex items-center space-x-3">
                                <Phone size={16} className="shrink-0 text-zomato" />
                                <span>+91 98765 43210</span>
                            </li>
                            <li className="flex items-center space-x-3">
                                <Mail size={16} className="shrink-0 text-zomato" />
                                <span>support@zomathon.com</span>
                            </li>
                        </ul>
                    </div>
                </div>

                <div className="border-t border-gray-800 mt-12 pt-8 flex flex-col md:flex-row justify-between items-center text-sm text-gray-500">
                    <p>By continuing past this page, you agree to our Terms of Service, Cookie Policy, Privacy Policy and Content Policies.</p>
                    <p className="mt-4 md:mt-0">© 2026 Zomathon. All rights reserved.</p>
                </div>
            </div>
        </footer>
    );
};

export default Footer;
