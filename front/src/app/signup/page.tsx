// "use client";

// import { useState } from "react";
// import { useRouter } from "next/navigation";
// import { signUp, confirmSignUp } from "aws-amplify/auth";

// export default function SignupPage() {
//   const [email, setEmail] = useState("");
//   const [password, setPassword] = useState("");
//   const [code, setCode] = useState("");
//   const [step, setStep] = useState<"signup" | "confirm">("signup");
//   const [showForm, setShowForm] = useState(false);
//   const [loading, setLoading] = useState(false);
//   const router = useRouter();

//   const handleSignup = async () => {
//     try {
//       setLoading(true);
//       await signUp({
//         username: email,
//         password,
//         options: { userAttributes: { email } },
//       });
//       setStep("confirm");
//     } catch (err: any) {
//       alert(err.message || "Error signing up");
//     } finally {
//       setLoading(false);
//     }
//   };

//   const handleConfirm = async () => {
//     try {
//       setLoading(true);
//       await confirmSignUp({ username: email, confirmationCode: code });
//       alert("✅ Signup confirmed! Redirecting to login...");
//       setTimeout(() => router.push("/login"), 1500);
//     } catch (err: any) {
//       alert(err.message || "Error confirming signup");
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
//       <div className="absolute top-1/2 left-10 transform -translate-y-1/2 flex gap-6 items-start">
//         {/* Trigger Button */}
//         {!showForm && (
//           <button
//             onClick={() => setShowForm(true)}
//             className="px-8 py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-[#0a0f2c] via-[#102a5c] to-[#1a3b7c] 
//                        shadow-lg border border-white/10 backdrop-blur-md transition-all duration-300 
//                        hover:scale-105 hover:-translate-y-1 hover:shadow-[0_0_30px_rgba(26,59,124,0.6)] hover:brightness-110"
//           >
//             Sign Up
//           </button>
//         )}

//         {/* Pop-Up Signup Form */}
//         <div
//           className={`transition-all duration-500 ease-out ${
//             showForm ? "opacity-100 scale-100" : "opacity-0 scale-95 pointer-events-none"
//           } w-full max-w-md`}
//         >
//           <div className="bg-gray-800/70 backdrop-blur-md p-8 rounded-xl shadow-2xl border border-gray-700 text-white transition-transform duration-300 hover:scale-105 hover:shadow-[0_0_25px_rgba(255,255,255,0.3)]">
//             <h2 className="text-3xl font-bold text-center mb-6 tracking-wide">Create Account</h2>

//             {step === "signup" && (
//               <>
//                 <input
//                   type="email"
//                   placeholder="Email"
//                   className="w-full px-4 py-2 mb-4 bg-gray-700 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
//                   onChange={(e) => setEmail(e.target.value)}
//                   value={email}
//                 />
//                 <input
//                   type="password"
//                   placeholder="Password"
//                   className="w-full px-4 py-2 mb-4 bg-gray-700 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
//                   onChange={(e) => setPassword(e.target.value)}
//                   value={password}
//                 />
//                 <button
//                   onClick={handleSignup}
//                   disabled={loading}
//                   className={`w-full py-2 rounded-xl font-semibold text-white bg-gradient-to-r from-[#0a0f2c] via-[#102a5c] to-[#1a3b7c] 
//                               shadow-lg border border-white/10 backdrop-blur-md transition-all duration-300 
//                               ${loading ? "cursor-not-allowed opacity-60" : "hover:scale-105 hover:-translate-y-1 hover:shadow-[0_0_30px_rgba(26,59,124,0.6)] hover:brightness-110"}`}
//                 >
//                   {loading ? "Signing Up..." : "Sign Up"}
//                 </button>
//               </>
//             )}

//             {step === "confirm" && (
//               <>
//                 <p className="text-sm mb-4 text-center">
//                   Enter the verification code sent to your email.
//                 </p>
//                 <input
//                   type="text"
//                   placeholder="Verification Code"
//                   className="w-full px-4 py-2 mb-4 bg-gray-700 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 transition"
//                   onChange={(e) => setCode(e.target.value)}
//                   value={code}
//                 />
//                 <button
//                   onClick={handleConfirm}
//                   disabled={loading}
//                   className={`w-full py-2 rounded-xl font-semibold text-white bg-gradient-to-r from-green-900 via-green-700 to-green-600 
//                               shadow-lg border border-white/10 backdrop-blur-md transition-all duration-300 
//                               ${loading ? "cursor-not-allowed opacity-60" : "hover:scale-105 hover:-translate-y-1 hover:shadow-[0_0_30px_rgba(0,255,0,0.4)] hover:brightness-110"}`}
//                 >
//                   {loading ? "Verifying..." : "Confirm Account"}
//                 </button>
//               </>
//             )}
//           </div>
//         </div>
//       </div>
//     </div>
//   );
// }

"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mail, Lock, Loader2, Sparkles, X, Shield, CheckCircle2, ArrowRight, Eye, EyeOff } from "lucide-react";
import { signUp, confirmSignUp } from "aws-amplify/auth";
import { useRouter } from "next/navigation";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"signup" | "confirm">("signup");
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [focusedInput, setFocusedInput] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const passwordRules = {
  length: password.length >= 8,
  uppercase: /[A-Z]/.test(password),
  lowercase: /[a-z]/.test(password),
  number: /[0-9]/.test(password),
  special: /[^A-Za-z0-9]/.test(password),
};

const isPasswordValid = Object.values(passwordRules).every(Boolean);


  const handleSignup = async () => {
    try {
      setLoading(true);
      await signUp({
        username: email,
        password,
        options: { userAttributes: { email } },
      });
      setStep("confirm");
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : "Error signing up";
      alert(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    try {
      setLoading(true);
      await confirmSignUp({ username: email, confirmationCode: code });
      alert("✅ Signup confirmed! Redirecting to login...");
      setTimeout(() => router.push("/login"), 1500);
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : "Error confirming signup";
      alert(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !loading) {
      if (step === "signup" && email && password) {
        handleSignup();
      } else if (step === "confirm" && code) {
        handleConfirm();
      }
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden bg-gradient-to-br from-indigo-950 via-purple-950 to-slate-900">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <motion.div
          className="absolute -top-1/2 -right-1/2 w-[1000px] h-[1000px] bg-purple-500/10 rounded-full blur-3xl"
          animate={{
            scale: [1, 1.3, 1],
            opacity: [0.2, 0.4, 0.2],
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
        <motion.div
          className="absolute -bottom-1/2 -left-1/2 w-[1000px] h-[1000px] bg-indigo-500/10 rounded-full blur-3xl"
          animate={{
            scale: [1.3, 1, 1.3],
            opacity: [0.2, 0.4, 0.2],
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 2,
          }}
        />
        <motion.div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-pink-500/5 rounded-full blur-3xl"
          animate={{
            scale: [1, 1.2, 1],
            rotate: [0, 180, 360],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: "linear",
          }}
        />
      </div>

      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.02)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_80%_50%_at_50%_50%,black,transparent)]" />

      {/* Floating particles */}
      {[...Array(20)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-1 h-1 bg-white/20 rounded-full"
          style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
          }}
          animate={{
            y: [0, -100, 0],
            opacity: [0, 1, 0],
          }}
          transition={{
            duration: 3 + Math.random() * 2,
            repeat: Infinity,
            delay: Math.random() * 2,
          }}
        />
      ))}

      {/* Content */}
      <div className="relative z-10 min-h-screen flex items-center px-4 sm:px-6 lg:px-8">
        <div className="w-full max-w-7xl mx-auto">
          <div className="flex flex-col lg:flex-row items-center justify-between gap-12 lg:gap-20">
            
            {/* Left side - Hero content */}
            <motion.div
              className="flex-1 text-center lg:text-left"
              initial={{ opacity: 0, x: -50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, ease: "easeOut" }}
            >
              <motion.div
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-purple-500/10 border border-purple-500/20 mb-6"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <Sparkles className="w-4 h-4 text-purple-400" />
                <span className="text-sm text-purple-300">Start your journey</span>
              </motion.div>

              <motion.h1
                className="text-5xl sm:text-6xl lg:text-7xl font-bold mb-6 bg-gradient-to-r from-white via-purple-100 to-pink-200 bg-clip-text text-transparent"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                Join Our
                <br />
                Community
              </motion.h1>

              <motion.p
                className="text-lg sm:text-xl text-slate-400 mb-8 max-w-lg mx-auto lg:mx-0"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                Create your account and unlock exclusive features designed to transform your experience.
              </motion.p>

              {/* Feature list */}
              <motion.div
                className="space-y-4 mb-8"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
              >
                {[
                  "Secure authentication",
                  "Personalized dashboard",
                  "24/7 support access",
                ].map((feature, i) => (
                  <motion.div
                    key={i}
                    className="flex items-center gap-3 text-slate-300"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.6 + i * 0.1 }}
                  >
                    <div className="flex-shrink-0 w-6 h-6 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center">
                      <CheckCircle2 className="w-4 h-4 text-white" />
                    </div>
                    <span>{feature}</span>
                  </motion.div>
                ))}
              </motion.div>

              <AnimatePresence mode="wait">
                {!showForm && (
                  <motion.button
                    onClick={() => setShowForm(true)}
                    className="group relative inline-flex items-center gap-3 px-8 py-4 rounded-2xl font-semibold text-white bg-gradient-to-r from-purple-600 via-pink-600 to-purple-600 shadow-lg shadow-purple-500/25 transition-all duration-300 hover:shadow-xl hover:shadow-purple-500/40 overflow-hidden"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    transition={{ delay: 0.8 }}
                    whileHover={{ scale: 1.05, y: -2 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <motion.div
                      className="absolute inset-0 bg-gradient-to-r from-purple-400 via-pink-400 to-purple-400"
                      animate={{
                        x: ["-100%", "100%"],
                      }}
                      transition={{
                        duration: 3,
                        repeat: Infinity,
                        ease: "linear",
                      }}
                      style={{ opacity: 0.3 }}
                    />
                    <span className="relative z-10">Create Account</span>
                    <motion.span
                      className="relative z-10"
                      animate={{ x: [0, 5, 0] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                    >
                      <ArrowRight className="w-5 h-5" />
                    </motion.span>
                  </motion.button>
                )}
              </AnimatePresence>
            </motion.div>

            {/* Right side - Signup form */}
            <div className="flex-1 w-full max-w-md">
              <AnimatePresence mode="wait">
                {showForm && (
                  <motion.div
                    initial={{ opacity: 0, x: 50, scale: 0.9 }}
                    animate={{ opacity: 1, x: 0, scale: 1 }}
                    exit={{ opacity: 0, x: 50, scale: 0.9 }}
                    transition={{ duration: 0.5, ease: "easeOut" }}
                    className="relative"
                  >
                    {/* Glow effect */}
                    <motion.div
                      className="absolute -inset-1 bg-gradient-to-r from-purple-600 via-pink-600 to-purple-600 rounded-3xl blur-xl opacity-30"
                      animate={{
                        opacity: [0.3, 0.5, 0.3],
                      }}
                      transition={{
                        duration: 3,
                        repeat: Infinity,
                        ease: "easeInOut",
                      }}
                    />

                    {/* Form container */}
                    <div className="relative bg-slate-900/80 backdrop-blur-xl p-8 sm:p-10 rounded-3xl border border-slate-800 shadow-2xl">
                      {/* Close button */}
                      <motion.button
                        onClick={() => setShowForm(false)}
                        className="absolute top-4 right-4 p-2 rounded-full bg-slate-800/50 hover:bg-slate-700/50 transition-colors z-50"
                        whileHover={{ scale: 1.1, rotate: 90 }}
                        whileTap={{ scale: 0.9 }}
                      >
                        <X className="w-5 h-5 text-slate-400" />
                      </motion.button>

                      {/* Progress indicator */}
                      <div className="flex items-center justify-center gap-2 mb-6">
                        <motion.div
                          className={`w-2 h-2 rounded-full ${
                            step === "signup" ? "bg-purple-500" : "bg-green-500"
                          }`}
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          transition={{ delay: 0.2 }}
                        />
                        <div className={`w-16 h-0.5 ${step === "confirm" ? "bg-green-500" : "bg-slate-700"}`} />
                        <motion.div
                          className={`w-2 h-2 rounded-full ${
                            step === "confirm" ? "bg-green-500" : "bg-slate-700"
                          }`}
                          animate={{
                            scale: step === "confirm" ? [0.8, 1.2, 1] : 1,
                          }}
                          transition={{ duration: 0.5 }}
                        />
                      </div>

                      <AnimatePresence mode="wait">
                        {step === "signup" ? (
                          <motion.div
                            key="signup"
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 20 }}
                            transition={{ duration: 0.3 }}
                          >
                            <div className="flex items-center justify-center mb-6">
                              <motion.div
                                className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center"
                                initial={{ scale: 0, rotate: -180 }}
                                animate={{ scale: 1, rotate: 0 }}
                                transition={{ delay: 0.3, type: "spring" }}
                              >
                                <Shield className="w-8 h-8 text-white" />
                              </motion.div>
                            </div>

                            <h2 className="text-3xl font-bold mb-2 text-center bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
                              Create Account
                            </h2>
                            <p className="text-slate-400 mb-8 text-center">
                              Join thousands of users today
                            </p>

                            {/* Email input */}
                            <div className="mb-5">
                              <label className="block text-sm font-medium text-slate-300 mb-2">
                                Email
                              </label>
                              <div className="relative group">
                                <Mail className={`absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 transition-colors ${
                                  focusedInput === "email" ? "text-purple-400" : "text-slate-500"
                                }`} />
                                <input
                                  type="email"
                                  placeholder="you@example.com"
                                  className="w-full pl-12 pr-4 py-3 bg-slate-800/50 text-white rounded-xl border border-slate-700 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 outline-none transition-all placeholder:text-slate-500"
                                  onChange={(e) => setEmail(e.target.value)}
                                  onFocus={() => setFocusedInput("email")}
                                  onBlur={() => setFocusedInput("")}
                                  onKeyPress={handleKeyPress}
                                  value={email}
                                />
                              </div>
                            </div>

                            {/* Password input */}
                            <div className="mb-6">
                              <label className="block text-sm font-medium text-slate-300 mb-2">
                                Password
                              </label>
                              <div className="relative group">
                                <Lock className={`absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 transition-colors ${
                                  focusedInput === "password" ? "text-purple-400" : "text-slate-500"
                                }`} />
                                <input
                                  type={showPassword ? "text" : "password"}
                                  placeholder="••••••••"
                                  className="w-full pl-12 pr-12 py-3 bg-slate-800/50 text-white rounded-xl border border-slate-700 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 outline-none transition-all placeholder:text-slate-500"
                                  onChange={(e) => setPassword(e.target.value)}
                                  onFocus={() => setFocusedInput("password")}
                                  onBlur={() => setFocusedInput("")}
                                  onKeyPress={handleKeyPress}
                                  value={password}
                                />
                                <button
                                  type="button"
                                  aria-label={showPassword ? "Hide password" : "Show password"}
                                  onClick={() => setShowPassword((v) => !v)}
                                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-purple-400 focus:outline-none"
                                  tabIndex={-1}
                                >
                                  {showPassword ? (
                                    <EyeOff className="h-5 w-5" />
                                  ) : (
                                    <Eye className="h-5 w-5" />
                                  )}
                                </button>
                              </div>

                              <div className="mt-3 space-y-1 text-xs">
                                <p className={passwordRules.length ? "text-pink-400" : "text-slate-500"}>
                                  • At least 8 characters
                                </p>
                                  <p className={passwordRules.uppercase ? "text-pink-400" : "text-slate-500"}>
                                  • One uppercase letter
                                  </p>
                                 <p className={passwordRules.lowercase ? "text-pink-400" : "text-slate-500"}>
                                 • One lowercase letter
                                  </p>
                                  <p className={passwordRules.number ? "text-pink-400" : "text-slate-500"}>
                                • One number
                                  </p>
                                  <p className={passwordRules.special ? "text-pink-400" : "text-slate-500"}>
                                 • One special character
                                  </p>
                                </div>
                                </div>
     

                            {/* Signup button */}
                            <motion.button
                              onClick={handleSignup}
                              disabled={loading || !email || !isPasswordValid}
                              className={`w-full py-4 rounded-xl font-semibold text-white transition-all duration-300 relative overflow-hidden ${
                                loading || !email || !isPasswordValid
                                  ? "bg-slate-700 cursor-not-allowed"
                                  : "bg-gradient-to-r from-purple-600 to-pink-600 hover:shadow-lg hover:shadow-purple-500/30"
                              }`}
                              whileHover={!loading && email && isPasswordValid ? { scale: 1.02, y: -2 } : {}}
                              whileTap={!loading && email && isPasswordValid ? { scale: 0.98 } : {}}
                            >
                              {loading && (
                                <motion.div
                                  className="absolute inset-0 bg-gradient-to-r from-purple-400 via-pink-400 to-purple-400"
                                  animate={{ x: ["-100%", "100%"] }}
                                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                                />
                              )}
                              <span className="relative z-10 flex items-center justify-center gap-2">
                                {loading ? (
                                  <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Creating account...
                                  </>
                                ) : (
                                  "Create Account"
                                )}
                              </span>
                            </motion.button>
                          </motion.div>
                        ) : (
                          <motion.div
                            key="confirm"
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 20 }}
                            transition={{ duration: 0.3 }}
                          >
                            <div className="flex items-center justify-center mb-6">
                              <motion.div
                                className="w-16 h-16 rounded-2xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center"
                                initial={{ scale: 0, rotate: -180 }}
                                animate={{ scale: 1, rotate: 0 }}
                                transition={{ delay: 0.3, type: "spring" }}
                              >
                                <Mail className="w-8 h-8 text-white" />
                              </motion.div>
                            </div>

                            <h2 className="text-3xl font-bold mb-2 text-center bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
                              Verify Email
                            </h2>
                            <p className="text-slate-400 mb-2 text-center">
                              We&apos;ve sent a code to
                            </p>
                            <p className="text-purple-400 mb-6 text-center font-medium">
                              {email}
                            </p>

                            {/* Code input */}
                            <div className="mb-6">
                              <label className="block text-sm font-medium text-slate-300 mb-2">
                                Verification Code
                              </label>
                              <input
                                type="text"
                                placeholder="Enter 6-digit code"
                                className="w-full px-4 py-3 bg-slate-800/50 text-white rounded-xl border border-slate-700 focus:border-green-500 focus:ring-2 focus:ring-green-500/20 outline-none transition-all placeholder:text-slate-500 text-center text-2xl tracking-widest"
                                onChange={(e) => setCode(e.target.value)}
                                onKeyPress={handleKeyPress}
                                value={code}
                                maxLength={6}
                              />
                            </div>

                            {/* Confirm button */}
                            <motion.button
                              onClick={handleConfirm}
                              disabled={loading || !code}
                              className={`w-full py-4 rounded-xl font-semibold text-white transition-all duration-300 relative overflow-hidden ${
                                loading || !code
                                  ? "bg-slate-700 cursor-not-allowed"
                                  : "bg-gradient-to-r from-green-600 to-emerald-600 hover:shadow-lg hover:shadow-green-500/30"
                              }`}
                              whileHover={!loading && code ? { scale: 1.02, y: -2 } : {}}
                              whileTap={!loading && code ? { scale: 0.98 } : {}}
                            >
                              {loading && (
                                <motion.div
                                  className="absolute inset-0 bg-gradient-to-r from-green-400 via-emerald-400 to-green-400"
                                  animate={{ x: ["-100%", "100%"] }}
                                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                                />
                              )}
                              <span className="relative z-10 flex items-center justify-center gap-2">
                                {loading ? (
                                  <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Verifying...
                                  </>
                                ) : (
                                  "Verify & Continue"
                                )}
                              </span>
                            </motion.button>

                            {/* Resend code */}
                            <div className="mt-4 text-center">
                              <button className="text-sm text-slate-400 hover:text-purple-400 transition-colors">
                                Didn&apos;t receive the code? Resend
                              </button>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>

                      {/* Terms */}
                      <motion.div
  className="text-center mt-6 space-y-2"
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
  transition={{ delay: 0.6 }}
>
  <p className="text-xs text-slate-500">
    By signing up, you agree to our{" "}
    <a href="/terms" className="text-purple-400 hover:underline">
      Terms
    </a>{" "}
    and{" "}
    <a href="/privacy" className="text-purple-400 hover:underline">
      Privacy Policy
    </a>.
  </p>

  <p className="text-sm text-slate-300">
    Already have an account?{" "}
    <button
      onClick={() => router.push("/login")}
      className="text-purple-400 hover:text-purple-300 underline underline-offset-4 transition"
    >
      Sign In
    </button>
  </p>
</motion.div>

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