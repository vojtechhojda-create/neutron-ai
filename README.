
#      Neutron-AI

## 📂 Jak to funguje?
do settings.json dáš svoje api a potom to stačí zapnout

## 🛠️ Instalace a spuštění

stáhni zde soubory a dej je do složky
         nebo otevři terminál a napiš
#### "git clone https://github.com/vojtechhojda-create/neutron-ai"


## Integrace Google Pay (1 Kč)

Tento projekt obsahuje ukázku integrace Google Pay tlačítka pro platbu v hodnotě 1 Kč (CZK). Pro funkčnost v produkčním prostředí je nutné kód propojit s vaší platební bránou.

### Použití

1. Zkopírujte níže uvedený kód do souboru `index.html`.
2. Nahraďte hodnoty `gateway` a `gatewayMerchantId` údaji od vaší platební brány.
3. Pro ostrý provoz změňte `environment: 'TEST'` na `'PRODUCTION'`.

```html
<!-- Kontejner pro Google Pay tlačítko -->
<div id="gpay-container"></div>

<script src="https://google.com"></script>
<script>
  const baseRequest = {
    apiVersion: 2,
    apiVersionMinor: 0
  };

  const tokenizationSpecification = {
    type: 'PAYMENT_GATEWAY',
    parameters: {
      'gateway': 'vložte_vaši_bránu', // např. 'stripe', 'comgate'
      'gatewayMerchantId': 'vaše_ID_obchodníka'
    }
  };

  const cardPaymentMethod = {
    type: 'CARD',
    parameters: {
      allowedAuthMethods: ['PAN_ONLY', 'CRYPTOGRAM_3DS'],
      allowedCardNetworks: ['MASTERCARD', 'VISA']
    },
    tokenizationSpecification: tokenizationSpecification
  };

  const paymentsClient = new google.payments.api.PaymentsClient({
    environment: 'TEST' // Změňte na 'PRODUCTION' pro ostrý web
  });

  const paymentDataRequest = Object.assign({}, baseRequest, {
    allowedPaymentMethods: [cardPaymentMethod],
    transactionInfo: {
      totalPriceStatus: 'FINAL',
      totalPrice: '1.00',   // Částka 1 Kč
      currencyCode: 'CZK',  // Měna CZK
      countryCode: 'CZ'
    },
    merchantInfo: {
      merchantName: 'Název Vašeho Obchodu'
    }
  });

  function initGooglePay() {
    const button = paymentsClient.createButton({
      onClick: () => {
        paymentsClient.loadPaymentData(paymentDataRequest)
          .then(paymentData => {
            console.log("Token úspěšně získán:", paymentData);
            // Zde odešlete token na váš server / platební bránu
          })
          .catch(err => {
            console.error("Chyba platby:", err);
          });
      }
    });
    document.getElementById('gpay-container').appendChild(button);
  }

  // Spuštění po načtení skriptu Google Pay
  window.onload = initGooglePay;
</script>
```

### Oficiální dokumentace
Pro více informací navštivte [Google Pay Web API Tutorial](https://google.com).
