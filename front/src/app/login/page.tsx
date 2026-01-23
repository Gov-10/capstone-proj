// "use client";

// import { useState } from "react";
// import { signIn, fetchAuthSession } from "aws-amplify/auth";
// import { useRouter } from "next/navigation";

// export default function LoginPage() {
//   const router = useRouter();
//   const [showLogin, setShowLogin] = useState(false);
//   const [email, setEmail] = useState("");
//   const [password, setPassword] = useState("");
//   const [loading, setLoading] = useState(false);

//   const handleLogin = async () => {
//     try {
//       setLoading(true);
//       await signIn({ username: email, password });
//       const session = await fetchAuthSession();
//       const token = session.tokens?.idToken?.toString();

//       if (token) localStorage.setItem("cognito_token", token);

//       alert("✅ Login successful!");
//       router.push("/dashboard");
//     } catch (err: any) {
//       alert(err.message || "Error logging in");
//     } finally {
//       setLoading(false);
//     }
//   };

//   return (
//     <div
//       className="min-h-screen bg-cover bg-center text-white px-4 relative"
//       style={{ backgroundImage: "url('/background-image.jpg')" }}
//     >
//       {/* Left-aligned container */}
//       <div className="absolute top-1/2 left-10 transform -translate-y-1/2 flex flex-row gap-6 items-start">
//         {/* Dark Gradient Login Button with Reversed Direction */}
//         {!showLogin && (
//                 <button
//         onClick={() => setShowLogin(true)}
//         className="px-8 py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-[#0a0f2c] via-[#102a5c] to-[#1a3b7c] 
//                     shadow-lg border border-white/10 backdrop-blur-md transition-all duration-300 
//                     hover:scale-105 hover:-translate-y-1 hover:shadow-[0_0_30px_rgba(26,59,124,0.6)] hover:brightness-110"
//         >
//         Login
//         </button>
//         )}

//         {/* Animated Login Form */}
//         <div
//           className={`transition-all duration-500 ease-out ${
//             showLogin ? "opacity-100 scale-100" : "opacity-0 scale-95 pointer-events-none"
//           } w-full max-w-md`}
//         >
//           <div className="bg-gray-800/70 backdrop-blur-md p-8 rounded-xl shadow-2xl border border-gray-700 text-white transition-transform duration-300 hover:scale-105 hover:shadow-[0_0_25px_rgba(255,255,255,0.3)]">
//             <h2 className="text-3xl font-bold text-center mb-6 tracking-wide">Login</h2>

//             <input
//               type="email"
//               placeholder="Email"
//               className="w-full px-4 py-2 mb-4 bg-gray-700 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
//               onChange={(e) => setEmail(e.target.value)}
//               value={email}
//             />
//             <input
//               type="password"
//               placeholder="Password"
//               className="w-full px-4 py-2 mb-4 bg-gray-700 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
//               onChange={(e) => setPassword(e.target.value)}
//               value={password}
//             />

//             <button
//               onClick={handleLogin}
//               disabled={loading}
//               className={`w-full py-2 rounded-lg font-semibold transition ${
//                 loading
//                   ? "bg-blue-400 cursor-not-allowed"
//                   : "bg-blue-600 hover:bg-blue-700"
//               }`}
//             >
//               {loading ? "Logging in..." : "Login"}
//             </button>
//           </div>
//         </div>
//       </div>
//     </div>
//   );
// }


"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mail, Lock, Loader2, Sparkles, X, Eye, EyeOff } from "lucide-react";
import { useRouter } from "next/navigation";
import { signIn } from "aws-amplify/auth";

export default function LoginPage() {
  const router = useRouter();
  const [showLogin, setShowLogin] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleLogin = async () => {
    try {
      setLoading(true);

      // 🔥 ACTUAL COGNITO LOGIN HERE
      const result = await signIn({
        username: email,
        password: password,
      });

      console.log("COGNITO LOGIN RESULT:", result);

      alert("✅ Logged in with Cognito!");
      router.push("/dashboard");

    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      console.error("Login error:", err);
      alert("❌ Login failed: " + errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !loading && email && password) {
      handleLogin();
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden bg-gradient-to-br from-slate-950 via-blue-950 to-slate-900">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <motion.div
          className="absolute -top-1/2 -right-1/2 w-[1000px] h-[1000px] bg-blue-500/10 rounded-full blur-3xl"
          animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.5, 0.3] }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute -bottom-1/2 -left-1/2 w-[1000px] h-[1000px] bg-purple-500/10 rounded-full blur-3xl"
          animate={{ scale: [1.2, 1, 1.2], opacity: [0.3, 0.5, 0.3] }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 1,
          }}
        />
      </div>

      {/* Grid overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.02)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_80%_50%_at_50%_50%,black,transparent)]" />

      {/* Content */}
      <div className="relative z-10 min-h-screen flex items-center px-4 sm:px-6 lg:px-8">
        <div className="w-full max-w-7xl mx-auto">
          <div className="flex flex-col lg:flex-row items-center justify-between gap-12 lg:gap-20">
            
            {/* Left side */}
            <motion.div
              className="flex-1 text-center lg:text-left"
              initial={{ opacity: 0, x: -50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, ease: "easeOut" }}
            >
              <motion.div
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/10 border border-blue-500/20 mb-6"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <Sparkles className="w-4 h-4 text-blue-400" />
                <span className="text-sm text-blue-300">Welcome back</span>
              </motion.div>

              <motion.h1
                className="text-5xl sm:text-6xl lg:text-7xl font-bold mb-6 bg-gradient-to-r from-white via-blue-100 to-blue-200 bg-clip-text text-transparent"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                Your Journey
                <br />
                Continues Here
              </motion.h1>

              <motion.p
                className="text-lg sm:text-xl text-slate-400 mb-8 max-w-lg mx-auto lg:mx-0"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                Access your dashboard and unlock powerful features.
              </motion.p>

              <AnimatePresence mode="wait">
                {!showLogin && (
                  <motion.button
                    onClick={() => setShowLogin(true)}
                    className="group relative inline-flex items-center gap-3 px-8 py-4 rounded-2xl font-semibold text-white bg-gradient-to-r from-blue-600 via-blue-500 to-purple-600 shadow-lg shadow-blue-500/25 transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/40 overflow-hidden"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    transition={{ delay: 0.5 }}
                    whileHover={{ scale: 1.05, y: -2 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <span className="relative z-10">Get Started →</span>
                  </motion.button>
                )}
              </AnimatePresence>
            </motion.div>

            {/* Right side - Form */}
            <div className="flex-1 w-full max-w-md">
              <AnimatePresence>
                {showLogin && (
                  <motion.div
                    initial={{ opacity: 0, x: 50, scale: 0.9 }}
                    animate={{ opacity: 1, x: 0, scale: 1 }}
                    exit={{ opacity: 0, x: 50, scale: 0.9 }}
                    transition={{ duration: 0.5, ease: "easeOut" }}
                  >
                    <div className="relative bg-slate-900/80 backdrop-blur-xl p-8 sm:p-10 rounded-3xl border border-slate-800 shadow-2xl">
                      <motion.button
                        onClick={() => setShowLogin(false)}
                        className="absolute top-4 right-4 p-2 rounded-full bg-slate-800/50 hover:bg-slate-700/50 transition-colors"
                      >
                        <X className="w-5 h-5 text-slate-400" />
                      </motion.button>

                      <h2 className="text-3xl font-bold mb-2 bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
                        Welcome Back
                      </h2>
                      <p className="text-slate-400 mb-8">
                        Sign in to continue
                      </p>

                      {/* Email */}
                      <div className="mb-5">
                        <label className="block text-sm font-medium text-slate-300 mb-2">Email</label>
                        <div className="relative">
                          <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                          <input
                            type="email"
                            placeholder="you@example.com"
                            className="w-full pl-12 pr-4 py-3 bg-slate-800/50 text-white rounded-xl border border-slate-700 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition-all"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            onKeyDown={handleKeyPress}
                          />
                        </div>
                      </div>

                      {/* Password */}
                      <div className="mb-6">
                        <label className="block text-sm font-medium text-slate-300 mb-2">Password</label>
                        <div className="relative">
                          <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                          <input
                            type={showPassword ? "text" : "password"}
                            placeholder="••••••••"
                            className="w-full pl-12 pr-12 py-3 bg-slate-800/50 text-white rounded-xl border border-slate-700 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition-all"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            onKeyDown={handleKeyPress}
                          />
                          <button
                            type="button"
                            aria-label={showPassword ? "Hide password" : "Show password"}
                            onClick={() => setShowPassword((v) => !v)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-blue-400 focus:outline-none"
                            tabIndex={-1}
                          >
                            {showPassword ? (
                              <EyeOff className="h-5 w-5" />
                            ) : (
                              <Eye className="h-5 w-5" />
                            )}
                          </button>
                        </div>
                      </div>

                      {/* Login Button */}
                      <motion.button
                        onClick={handleLogin}
                        disabled={loading || !email || !password}
                        className={`w-full py-4 rounded-xl font-semibold text-white transition-all duration-300 ${
                          loading || !email || !password
                            ? "bg-slate-700 cursor-not-allowed"
                            : "bg-gradient-to-r from-blue-600 to-purple-600 hover:shadow-lg hover:shadow-blue-500/30"
                        }`}
                      >
                        {loading ? (
                          <span className="flex items-center justify-center gap-2">
                            <Loader2 className="w-5 h-5 animate-spin" />
                            Signing in...
                          </span>
                        ) : (
                          "Sign In"
                        )}
                      </motion.button>

                      <div className="mt-6 text-center space-y-3">
                        <a href="#" className="text-sm text-slate-400 hover:text-blue-400 block">
                          Forgot your password?
                        </a>
                        
                        <p className="text-xs text-slate-500">
                          By signing in, you agree to our{" "}
                          <a href="/terms" className="text-blue-400 hover:underline">
                            Terms
                          </a>{" "}
                          and{" "}
                          <a href="/privacy" className="text-blue-400 hover:underline">
                            Privacy Policy
                          </a>.
                        </p>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
