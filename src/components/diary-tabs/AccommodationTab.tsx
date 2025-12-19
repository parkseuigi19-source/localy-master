import { motion } from 'motion/react';
import { Home, Star, MapPin } from 'lucide-react';

export function AccommodationTab() {
  const accommodations = [
    {
      id: 1,
      name: 'Riverside Inn',
      location: 'Mountain Valley',
      rating: 4.8,
      notes: 'Traditional Japanese-style rooms with river view',
    },
    {
      id: 2,
      name: 'Sakura Guesthouse',
      location: 'Countryside Village',
      rating: 4.9,
      notes: 'Family-run, homemade breakfast included',
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className="space-y-6"
    >
      <div className="flex items-center gap-3 mb-8">
        <div className="p-3 bg-[#4ECDC4]/10 rounded-full">
          <Home className="w-6 h-6 text-[#4ECDC4]" />
        </div>
        <h2 className="text-[#8B4513]" style={{ fontFamily: 'Georgia, serif', fontSize: '2rem' }}>
          Accommodations
        </h2>
      </div>

      <div className="space-y-4">
        {accommodations.map((place, index) => (
          <motion.div
            key={place.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="p-5 bg-white/50 rounded-lg border-2 border-[#8B4513]/10 hover:border-[#4ECDC4]/30 transition-colors"
          >
            <div className="flex items-start justify-between mb-3">
              <h3 className="text-[#8B4513]" style={{ fontSize: '1.25rem' }}>
                {place.name}
              </h3>
              <div className="flex items-center gap-1">
                <Star className="w-4 h-4 text-[#FFE66D] fill-[#FFE66D]" />
                <span className="text-gray-600">{place.rating}</span>
              </div>
            </div>
            
            <div className="flex items-center gap-2 mb-3">
              <MapPin className="w-4 h-4 text-[#4ECDC4]" />
              <span className="text-gray-600" style={{ fontSize: '0.875rem' }}>
                {place.location}
              </span>
            </div>
            
            <p className="text-gray-600 italic border-l-2 border-[#4ECDC4] pl-3" style={{ fontSize: '0.875rem' }}>
              {place.notes}
            </p>
          </motion.div>
        ))}
      </div>

      <motion.button
        className="w-full mt-6 p-4 bg-[#4ECDC4]/10 hover:bg-[#4ECDC4]/20 rounded-lg border-2 border-dashed border-[#4ECDC4]/30 text-[#8B4513] transition-colors"
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        + Add accommodation
      </motion.button>
    </motion.div>
  );
}
