"use client"
import { motion } from "framer-motion"

import { cn } from "@/lib/utils"

import type React from "react"

export const BackgroundGradient = ({
  children,
  className,
  containerClassName,
  animate = true,
}: {
  children?: React.ReactNode
  className?: string
  containerClassName?: string
  animate?: boolean
}) => {
  const variants = {
    initial: {
      backgroundPosition: "0 50%",
    },
    animate: {
      backgroundPosition: ["0, 50%", "100% 50%", "0 50%"],
    },
  }
  return (
    <div className={cn("relative p-[4px] group", containerClassName)}>
      <motion.div
        variants={animate ? variants : undefined}
        initial={animate ? "initial" : undefined}
        animate={animate ? "animate" : undefined}
        transition={
          animate
            ? {
                duration: 5,
                repeat: Number.POSITIVE_INFINITY,
                repeatType: "reverse",
              }
            : undefined
        }
        style={{
          backgroundSize: animate ? "400% 400%" : undefined,
        }}
        className={cn(
          "absolute inset-0 rounded-3xl z-[1] opacity-60 group-hover:opacity-100 blur-xl  transition duration-500 will-change-transform",
          " bg-[radial-gradient(circle_farthest-side_at_0_100%,#FFD700,transparent),radial-gradient(circle_farthest-side_at_100_0,#161e3a,transparent),radial-gradient(circle_farthest-side_at_100_100%,#F0EAD6,transparent),radial-gradient(circle_farthest-side_at_0_0,#161e3a,#161e3a)]",
        )}
      />
      <motion.div
        variants={animate ? variants : undefined}
        initial={animate ? "initial" : undefined}
        animate={animate ? "animate" : undefined}
        transition={
          animate
            ? {
                duration: 5,
                repeat: Number.POSITIVE_INFINITY,
                repeatType: "reverse",
              }
            : undefined
        }
        style={{
          backgroundSize: animate ? "400% 400%" : undefined,
        }}
        className={cn(
          "absolute inset-0 rounded-3xl z-[1] will-change-transform",
          "bg-[radial-gradient(circle_farthest-side_at_0_100%,#FFD700,transparent),radial-gradient(circle_farthest-side_at_100_0,#161e3a,transparent),radial-gradient(circle_farthest-side_at_100_100%,#F0EAD6,transparent),radial-gradient(circle_farthest-side_at_0_0,#161e3a,#161e3a)]",
        )}
      />

      <div className={cn("relative z-10", className)}>{children}</div>
    </div>
  )
}
