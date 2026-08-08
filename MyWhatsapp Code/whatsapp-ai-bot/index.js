const express = require('express');
const fetch = require('node-fetch');
const app = express();
app.use(express.json());

const PHONE_NUMBER_ID = '1159486830587819';
const ACCESS_TOKEN = process.env.WHATSAPP_ACCESS_TOKEN || 'EAAgrNOXPROoBRyGxQxrXyZBkOIhEkuAmrO3ZALy2AhYqzAKsFVzcHvVls52k3dOmZCnap2jlRJC5PXi7ZAVIItPgAJk3NJJ1RGAMh4j9fbaVREZC9etJjoYYfzTmNTW3Sqh7lpRvqhSvkPTGlFV5jd7bQ1OPPPrZCsgABV4o1CZAdpw3aqENmAmG5IYLD21B7SvRfNICfPzITnLNa5ZBCxtS5oiQ4EHTOfTAPUMJe0mwlhqjy85Y29pvt8DTLzvPcrSPlGAqzZBAYovHRtJ3UcD307wZDZD';

app.get('/webhook', (req, res) => {
    const mode = req.query['hub.mode'];
    const token = req.query['hub.verify_token'];
    const challenge = req.query['hub.challenge'];
    if (mode === 'subscribe' && token === 'ZeeSolutionHubSecretAI') {
        res.status(200).send(challenge);
    } else {
        res.sendStatus(403);
    }
});

app.post('/webhook', async (req, res) => {
    console.log('Meta se data aaya:', JSON.stringify(req.body, null, 2));

    const body = req.body;
    const message = body.entry?.[0]?.changes?.[0]?.value?.messages?.[0];

    if (message) {
        const senderNumber = message.from;

        console.log(`Message received from: ${senderNumber}`);
        console.log(`Message text: ${message.text?.body}`);

        await sendWhatsAppMessage(
            PHONE_NUMBER_ID,
            senderNumber,
            'Assalam-o-Alaikum! Zee Solution Hub se rabta karne ka shukriya. Hum aapko jald hi respond karenge.'
        );
    } else {
        console.log('Koi message nahi mila — shayad status update ya webhook test event hai.');
    }

    res.status(200).send('EVENT_RECEIVED');
});

async function sendWhatsAppMessage(phoneNumberId, toNumber, text) {
    if (ACCESS_TOKEN === 'YOUR_META_ACCESS_TOKEN_HERE') {
        console.error('ACCESS_TOKEN set nahi hai! Meta Dashboard se token paste karein.');
        return;
    }

    try {
        console.log('Reply bhej rahe hain:', toNumber);
        const response = await fetch(`https://graph.facebook.com/v25.0/${phoneNumberId}/messages`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${ACCESS_TOKEN}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                messaging_product: 'whatsapp',
                to: toNumber,
                type: 'text',
                text: { body: text }
            })
        });

        const data = await response.json();
        console.log('API Status:', response.status);
        console.log('API Response:', JSON.stringify(data, null, 2));

        if (!response.ok) {
            console.error('Meta API ne reply reject kar diya — token ya permissions check karein.');
        }
    } catch (err) {
        console.error('Error sending message via Meta API:', err);
    }
}

app.listen(3000, () => console.log('Server running on port 3000'));
