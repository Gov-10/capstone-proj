"use client";
import Link from 'next/link';
import { getCurrentUser, signOut } from 'aws-amplify/auth';
import { Hub } from 'aws-amplify/utils';
import React, { useState, useEffect } from 'react';

interface User {
    userId: string;
    username: string;
}

const Navbar = () => {
    const [isScrolled, setIsScrolled] = useState(false);
    const [user, setUser] = useState<User | null>(null);

    useEffect(() => {
        const handleScroll = () => {
            if (window.scrollY > 10) {
                setIsScrolled(true);
            } else {
                setIsScrolled(false);
            }
        };

        const checkUser = async () => {
            try {
                const currentUser = await getCurrentUser();
                setUser(currentUser as User);
            } catch {
                setUser(null);
            }
        };

        window.addEventListener("scroll", handleScroll);
        checkUser();

    const hubListener = Hub.listen("auth", ({ payload }) => {
      if (payload.event === "signedIn") {
        checkUser();
      } else if (payload.event === "signedOut") {
        setUser(null);
      }
    });

    return () => {
      window.removeEventListener("scroll", handleScroll);
      hubListener();
    };
  }, []);

  const handleLogout = async () => {
    try {
      await signOut();
      window.location.href = "/";
    } catch (error) {
      console.error("Error signing out: ", error);
    }
  };

  return (
    <nav className="fixed top-0 left-0 w-full z-50 bg-transparent">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link
              href="/"
              className="text-2xl font-bold bg-gradient-to-r from-purple-400 via-pink-500 to-red-500 bg-clip-text text-transparent hover:opacity-90 transition-opacity"
            >
              LegalSummariser
            </Link>
          </div>

          {/* Center nav links */}
          <div className="hidden md:block">
            <div className="ml-10 flex items-baseline space-x-8">
              <Link
                href="/"
                className="text-slate-200 hover:text-purple-300 px-3 py-2 text-sm font-medium transition-all hover:-translate-y-0.5 relative group"
              >
                Home
                <span className="absolute bottom-0 left-0 w-0 h-[2px] bg-gradient-to-r from-purple-400 to-pink-500 transition-all duration-300 group-hover:w-full" />
              </Link>
              <Link
                href="/signup"
                className="text-slate-200 hover:text-purple-300 px-3 py-2 text-sm font-medium transition-all hover:-translate-y-0.5 relative group"
              >
                Sign Up
                <span className="absolute bottom-0 left-0 w-0 h-[2px] bg-gradient-to-r from-purple-400 to-pink-500 transition-all duration-300 group-hover:w-full" />
              </Link>
              <Link
                href="/login"
                className="text-slate-200 hover:text-purple-300 px-3 py-2 text-sm font-medium transition-all hover:-translate-y-0.5 relative group"
              >
                Login
                <span className="absolute bottom-0 left-0 w-0 h-[2px] bg-gradient-to-r from-purple-400 to-pink-500 transition-all duration-300 group-hover:w-full" />
              </Link>
            </div>
          </div>

          {/* Right: dashboard / logout */}
          <div>
            {user ? (
              <div className="flex items-center space-x-4">
                <Link
                  href="/dashboard"
                  className="bg-white/10 hover:bg-white/20 text-white px-6 py-2 rounded-full text-sm font-medium transition-all backdrop-blur-sm border border-white/10 hover:border-purple-500/50 shadow-lg hover:shadow-purple-500/20 active:scale-95"
                >
                  Dashboard
                </Link>
                <button
                  onClick={handleLogout}
                  className="bg-red-500/10 hover:bg-red-500/20 text-red-200 px-6 py-2 rounded-full text-sm font-medium transition-all backdrop-blur-sm border border-red-500/10 hover:border-red-500/50 shadow-lg hover:shadow-red-500/20 active:scale-95"
                >
                  Logout
                </button>
              </div>
            ) : (
              <></>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
