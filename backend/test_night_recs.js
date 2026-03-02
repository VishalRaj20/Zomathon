import axios from 'axios';

async function testNightTime() {
    try {
        const res = await axios.post("http://localhost:8000/recommend", {
            user_id: 1,
            restaurant_id: 0,
            cart_items: [],
            timestamp: "2024-11-15T21:30:00"
        });

        console.log("Night Time Empty Cart Recommendations:");
        res.data.recommendations.forEach(r => {
            console.log(`- [Cat: ${r.category}] ${r.name}`);
        });
    } catch (err) {
        console.error("API error", err.message);
    }
}

testNightTime();
