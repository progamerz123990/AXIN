# AXIN Firebase Backend — starter package

This package adds a Firebase Cloud Functions starter backend for AXIN. It does not modify the ESP32 firmware or XiaoZhi Wi-Fi provisioning flow.

## Included files

- `firebase.json` — Firebase CLI configuration.
- `firestore.rules` — blocks direct client access to server-managed AXIN data.
- `functions/package.json` — Node.js dependencies.
- `functions/index.js` — authenticated HTTPS chat function, Gemini call, and Firestore history.
- `functions/AXIN_System_Personality_Prompt_v1.md` — AXIN personality prompt copied from the existing repository file.

## Before deployment

1. Open your Firebase project in the Firebase Console.
2. Enable Firebase Authentication and at least one sign-in provider.
3. Create a Cloud Firestore database.
4. Confirm that Cloud Functions deployment and billing requirements are satisfied for your project.
5. Use a computer or a supported terminal environment with Node.js 22 and Firebase CLI installed.
6. From the repository root, run `firebase login`, then `firebase use --add` and select your actual Firebase project. This creates `.firebaserc` locally; do not guess the project ID.
7. Set the Gemini key as a Firebase secret: `firebase functions:secrets:set GEMINI_API_KEY`. Do not put the key in GitHub or in ESP32 firmware.
8. Run `cd functions && npm install && cd ..`.
9. Deploy with `firebase deploy --only functions,firestore:rules`.

## API contract

Send a POST request to the deployed `axinChat` function URL with a Firebase Authentication ID token:

`Authorization: Bearer FIREBASE_ID_TOKEN`

JSON body:

```json
{
  "conversation_id": "default",
  "message": "Hello AXIN"
}
```

The function derives the Firestore user path from the verified token, so a caller cannot choose another user's UID. Conversation messages are stored under `users/{verifiedUid}/conversations/{conversationId}/messages`.

## Important limitations before production

- This is a cloud-backend starter, not a finished hardware integration.
- Device pairing, audio streaming, speech-to-text, text-to-speech, App Check, per-user quotas, and rate limiting are not implemented yet.
- CORS is currently permissive (`*`) but Firebase ID-token authentication is still required. Restrict CORS to the actual app origin(s) before production.
- The default model is `gemini-2.5-flash`. Verify that this model is available to your Gemini API project before deployment; set `AXIN_GEMINI_MODEL` to a supported model if needed.
- Do not upload API keys, passwords, tokens, or Firebase service-account files to GitHub.
- Keep the existing XiaoZhi Wi-Fi provisioning code unchanged during this cloud-backend stage.
