import { motion } from "framer-motion";

export default function HeroSectionWrapper({
  children,
  className,
  style,
  ...props
}) {
  return (
    <motion.section
      style={style}
      className={`h-screen w-full ${className}`}
      {...props}
    >
      {children}
    </motion.section>
  );
}
