"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useStore } from "@/lib/store";
import toast from "react-hot-toast";

export default function AuthPage() {
  const router = useRouter();
  const { setCurrentUser, setToken } = useStore();
  const [mode, setMode] = useState<"login" | "register" | "otp">("login");
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);

  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [otp, setOtp] = useState("");

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await api.login({ phone, password });
      localStorage.setItem("token", data.access_token);
      setToken(data.access_token);
      setCurrentUser(data.user);
      router.push("/");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    if (step === 1) {
      if (!phone.trim() || !password.trim()) {
        toast.error("Phone and password are required");
        return;
      }
      setStep(2);
      return;
    }
    if (step === 2) {
      // Send OTP (mocked — always use 123456)
      toast.success("OTP sent! Use 123456 for testing");
      setStep(3);
      return;
    }
    // Step 3: verify OTP and complete registration
    setLoading(true);
    try {
      const data = await api.register({
        phone,
        password,
        username,
        display_name: displayName || username,
        otp,
      });
      localStorage.setItem("token", data.access_token);
      setToken(data.access_token);
      setCurrentUser(data.user);
      router.push("/");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#008069] via-[#005c4b] to-[#002b22]">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm mx-4 overflow-hidden">
        {/* Header */}
        <div className="bg-[#008069] px-6 py-8 text-center">
          <div className="w-16 h-16 rounded-full bg-white/20 flex items-center justify-center mx-auto mb-3">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="white">
              <path d="M20.01 15.38c-1.23 0-2.42-.2-3.53-.56-.35-.12-.74-.03-1.01.24l-1.57 1.97c-2.83-1.35-5.48-3.9-6.89-6.83l1.95-1.66c.27-.28.35-.67.24-1.02-.37-1.11-.56-2.3-.56-3.53 0-.54-.45-.99-.99-.99H4.19C3.65 3 3 3.24 3 3.99 3 13.28 10.73 21 20.01 21c.71 0 .99-.63.99-1.18v-3.45c0-.54-.45-.99-.99-.99z"/>
            </svg>
          </div>
          <h1 className="text-white text-2xl font-light">Signal</h1>
          <p className="text-green-200 text-sm mt-1">Private messaging, simplified</p>
        </div>

        <div className="p-6">
          {/* Tabs */}
          <div className="flex mb-6 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => { setMode("login"); setStep(1); }}
              className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors ${
                mode === "login" ? "bg-white text-[#008069] shadow-sm" : "text-gray-500"
              }`}
            >
              Sign in
            </button>
            <button
              onClick={() => { setMode("register"); setStep(1); }}
              className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors ${
                mode === "register" ? "bg-white text-[#008069] shadow-sm" : "text-gray-500"
              }`}
            >
              Register
            </button>
          </div>

          {mode === "login" ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Phone number</label>
                <input
                  type="text"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+1234567890"
                  required
                  className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#008069] focus:ring-1 focus:ring-[#008069]"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#008069] focus:ring-1 focus:ring-[#008069]"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-[#008069] text-white rounded-lg font-medium text-sm hover:bg-[#006a5a] disabled:opacity-60 transition-colors"
              >
                {loading ? "Signing in..." : "Sign in"}
              </button>
              <div className="text-center text-xs text-gray-400">
                Demo: +1234567890 / password123
              </div>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="space-y-4">
              {/* Progress indicator */}
              <div className="flex gap-1 mb-2">
                {[1, 2, 3].map((s) => (
                  <div
                    key={s}
                    className={`flex-1 h-1 rounded-full ${step >= s ? "bg-[#008069]" : "bg-gray-200"}`}
                  />
                ))}
              </div>
              <p className="text-xs text-gray-400 text-center">
                Step {step} of 3
              </p>

              {step === 1 && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Phone number</label>
                    <input
                      type="text"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="+1234567899"
                      required
                      className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#008069]"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Password</label>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Min 6 characters"
                      required
                      className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#008069]"
                    />
                  </div>
                </>
              )}

              {step === 2 && (
                <div className="text-center py-4">
                  <div className="text-4xl mb-3">📱</div>
                  <p className="text-sm text-gray-600">We'll send an OTP to</p>
                  <p className="font-medium text-gray-900">{phone}</p>
                  <p className="text-xs text-gray-400 mt-2">
                    (Demo: use 123456)
                  </p>
                </div>
              )}

              {step === 3 && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">OTP Code</label>
                    <input
                      type="text"
                      value={otp}
                      onChange={(e) => setOtp(e.target.value)}
                      placeholder="123456"
                      maxLength={6}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#008069] text-center text-xl tracking-widest"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Username</label>
                    <input
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder="e.g. johndoe"
                      required
                      className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#008069]"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Display name</label>
                    <input
                      type="text"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      placeholder="Your name"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-[#008069]"
                    />
                  </div>
                </>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-[#008069] text-white rounded-lg font-medium text-sm hover:bg-[#006a5a] disabled:opacity-60"
              >
                {loading ? "Please wait..." : step < 3 ? "Continue →" : "Create account"}
              </button>
            </form>
          )}
        </div>

        <div className="px-6 pb-4 text-center">
          <p className="text-xs text-gray-400 flex items-center justify-center gap-1">
            🔒 End-to-end encrypted
          </p>
        </div>
      </div>
    </div>
  );
}
