import axios from 'axios';

async function testBurgerCart() {
    try {
        const res = await axios.post("http://localhost:8000/recommend", {
            user_id: 1,
            restaurant_id: 0,
            cart_items: [43], // Burger ID
            timestamp: new Date().toISOString()
        });

        console.log("Burger Cart Recommendations:");
        res.data.recommendations.forEach(r => {
            console.log(`- [Cat: ${r.category}] ${r.name}`);
        });
    } catch (err) {
        console.error("API error", err.message);
    }
}

testBurgerCart();
