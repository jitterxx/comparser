CREATE DATABASE  IF NOT EXISTS `clear_data` /*!40100 DEFAULT CHARACTER SET utf8 */;
USE `clear_data`;
-- MySQL dump 10.13  Distrib 5.5.46, for debian-linux-gnu (x86_64)
--
-- Host: 127.0.0.1    Database: clear_data
-- ------------------------------------------------------
-- Server version	5.5.46-0ubuntu0.14.04.2

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `email_cleared_data`
--

DROP TABLE IF EXISTS `email_cleared_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `email_cleared_data` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `message_id` varchar(255) DEFAULT NULL,
  `sender` varchar(255) DEFAULT NULL,
  `sender_name` varchar(255) DEFAULT NULL,
  `recipients` text,
  `recipients_name` text,
  `cc_recipients` text,
  `cc_recipients_name` text,
  `message_title` text,
  `message_text` mediumtext,
  `orig_date` datetime DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `isclassified` int(11) DEFAULT '0',
  `category` varchar(255) DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `email_cleared_data`
--

LOCK TABLES `email_cleared_data` WRITE;
/*!40000 ALTER TABLE `email_cleared_data` DISABLE KEYS */;
/*!40000 ALTER TABLE `email_cleared_data` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `email_err_cleared_data`
--

DROP TABLE IF EXISTS `email_err_cleared_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `email_err_cleared_data` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `message_id` varchar(255) DEFAULT NULL,
  `sender` varchar(255) DEFAULT NULL,
  `sender_name` varchar(255) DEFAULT NULL,
  `recipients` text,
  `recipients_name` text,
  `cc_recipients` text,
  `cc_recipients_name` text,
  `message_title` text,
  `message_text` mediumtext,
  `orig_date` datetime DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `email_err_cleared_data`
--

LOCK TABLES `email_err_cleared_data` WRITE;
/*!40000 ALTER TABLE `email_err_cleared_data` DISABLE KEYS */;
/*!40000 ALTER TABLE `email_err_cleared_data` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2015-11-02 17:32:38
