import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('passkeys_tour_login', {
    url: '/odoo',
    steps: () => [
        {
            content: "Inject authenticator data",
            trigger: 'body',
            run: () => {
                // !! REVIEW !!
                // Even worse than the prototype hack, but no way around it, using publicWidget
                // in a test causes a dependency error as soon as you are logged in.
                globalThis.PASSKEY_TEST_AUTH = {
                    "id": "y6aJVJsvvSSkbwTeGZ1FbQP_jCDho7EBPwZq-3lAjQ0",
                    "rawId": "y6aJVJsvvSSkbwTeGZ1FbQP_jCDho7EBPwZq-3lAjQ0",
                    "response": {
                        "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MFAAAAAA",
                        "clientDataJSON": "eyJjaGFsbGVuZ2UiOiJMTnBWMGRQSU10bXBTd0dlbklIX2gxVnljUXVBZ0ZnUVJKOVRQS0JvTmF5U2NOQUVyUy1yc25hVTE5bjdfQWFYemVpWVJnM25HSTN5dUgwYWk2VVBYQSIsImNyb3NzT3JpZ2luIjpmYWxzZSwib3JpZ2luIjoiaHR0cHM6Ly9sb2NhbGhvc3Q6ODg4OCIsInR5cGUiOiJ3ZWJhdXRobi5nZXQifQ",
                        "signature": "MEYCIQCqkh2NBQQao5uDTaBKyNhiEpnk4jgbH-PjdLAul9-d0gIhAMObtNTbaEMUILdNgCT01BKNN4NHRzkzsGaDN2Ozu0WX",
                        "userHandle": "Ng"
                    },
                    "type": "public-key",
                    "clientExtensionResults": {},
                    "authenticatorAttachment": "platform",
                };
            }
        }, {
            content: 'Login with Passkey',
            trigger: 'button:contains("Log in with Passkey")',
            run: 'click',
        }, {
            content: 'Check if we are logged in',
            trigger: '.o_user_menu .dropdown-toggle',
        }
    ]
})
