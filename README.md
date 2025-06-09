# Betygsbevakare-inspera

 Hur funkar jag?

Jag är byggd med Python och använder Playwright för att automatisera webbläsarinteraktioner. Jag autentiserar med hjälp av pseudo inloggningsuppgifter via Insperas SSO och navigerar automatiskt till kursens resultatsida. Genom DOM-parsning identifierar jag specifika HTML-element där betyget visas. Om betyget inte finns direkt, letar jag efter granskningsvyn och extraherar informationen därifrån. Jag körs i en schemalagd loop och skickar notifieringar via SMTP när betyg uppdateras. All känslig information hanteras via en .env-fil för säkerhet och konfigurationshantering.

---

Är jag pålitlig?

Jag använder samma inloggning som du gör, men körs från en säker lokal miljö. All trafik är krypterad. Betyget hämtas direkt från Insperas publika gränssnitt – inget manipuleras eller förfalskas.
