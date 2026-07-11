
#      Neutron-AI

## 📂 Jak to funguje?
do settings.json dáš svoje api a potom to stačí zapnout

## 🛠️ Instalace a spuštění

stáhni zde soubory a dej je do složky
         nebo otevři terminál a napiš
#### "git clone https://github.com/vojtechhojda-create/neutron-ai"


<!-- Kontejner, kam se Google Pay tlačítko vyrenderuje -->
<div id="container"></div>

<script src="https://google.com"></script>
<script>
  /**
   * Základní konfigurace pro Google Pay
   */
  const baseRequest = {
    apiVersion: 2,
    apiVersionMinor: 0
  };

  const tokenizationSpecification = {
    type: 'PAYMENT_GATEWAY',
    parameters: {
      'gateway': 'vložte_vaši_platební_bránu', // např. 'stripe', 'adyen', 'comgate'
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
    environment: 'TEST' // Pro produkci změňte na 'PRODUCTION'
  });

  /**
   * Nastavení transakce
   */
  const paymentDataRequest = Object.assign({}, baseRequest, {
    allowedPaymentMethods: [cardPaymentMethod],
    transactionInfo: {
      totalPriceStatus: 'FINAL',
      totalPrice: '1.00', // Částka
      currencyCode: 'CZK', // Měna
      countryCode: 'CZ'
    },
    merchantInfo: {
      merchantName: 'Název vašeho obchodu'
    }
  });

  /**
   * Vytvoření a vložení tlačítka
   */
  function addGooglePayButton() {
    const button = paymentsClient.createButton({
      onClick: () => {
        paymentsClient.loadPaymentData(paymentDataRequest)
          .then(function(paymentData) {
            // Zde zpracujte platební token vrácený z Google Pay
            console.log("Platba úspěšná:", paymentData);
          })
          .catch(function(err) {
            console.error("Chyba při platbě:", err);
          });
      }
    });
    document.getElementById('container').appendChild(button);
  }

  // Inicializace po načtení skriptu
  onGooglePayLoaded();
</script>
